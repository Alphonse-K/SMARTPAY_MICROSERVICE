import time
import requests
from urllib.parse import urlencode
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import hashlib
from smartpay_integration.models import SmartPayToken
import hmac
import logging
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware

logger = logging.getLogger(__name__)



class SmartPayService:
    def __init__(self):
        self.base_url = settings.SMARTPAY_CONFIG['BASE_URL']
        self.user = settings.SMARTPAY_CONFIG['API_USER']
        self.password = settings.SMARTPAY_CONFIG['API_PASSWORD']
        self.sign_type = settings.SMARTPAY_CONFIG['SIGN_TYPE']
        self.token_expiry = settings.SMARTPAY_CONFIG['TOKEN_EXPIRY_HOURS']
        self.current_token = self._get_active_token()


    def _generate_seed(self):
        """Generate an random seed for each request"""
        return hashlib.md5(str(time.time()).encode()).hexdigest().upper()
    
    def _calculate_key(self, seed, token=None):
        """Calculate the key for signature as per SMARTPAY docs"""
        try:
            # Step 1: Calculate Pass (HMAC-SHA256 of password)
            pass_hash = hmac.new(
                self.password.encode(),
                self.password.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Step 2: Calculate value (MD5 of user + pass_hash + token)
            token_value = token.token if token else ''
            value_str = f"{self.user}{pass_hash}{token_value}"
            value = hashlib.md5(value_str.encode()).hexdigest()
            
            # Step 3: Calculate key (MD5 of value + seed)
            key_str = f"{value}{seed}"
            return hashlib.md5(key_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating the key: {str(e)}")
            raise

    def _generate_signature(self, params, seed, token=None):
        """Generate signature for request"""
        try:
            # Remove empty params and sort
            clean_params = {k: v for k, v in params.items() if v not in [None, ""]}
            sorted_params = sorted(clean_params.items(), key=lambda x: x[0])
            
            # Create stringA in format key1=value1&key2=value2
            stringA = urlencode(sorted_params)
            
            # Calculate key
            key = self._calculate_key(seed, token)
            
            # IMPORTANT FIX: Add &key= before the key value
            stringSignTemp = f"{stringA}&key={key}"
            
            if self.sign_type == 'MD5':
                return hashlib.md5(stringSignTemp.encode()).hexdigest().upper()
            elif self.sign_type == 'HMAC-SHA256':
                return hmac.new(
                    key.encode(),
                    stringSignTemp.encode(),
                    hashlib.sha256
                ).hexdigest().upper()
            else:
                raise ValueError(f"Unsupported sign type: {self.sign_type}")
        except Exception as e:
            logger.error(f"Error generating signature: {str(e)}")
            raise


    def _get_active_token(self):
        """Get or create active token with proper datetime handling"""
        try:
            buffer_time = timezone.now() + timedelta(minutes=5)
            active_tokens = SmartPayToken.objects.filter(is_active=True)
            
            for token in active_tokens:
                # Handle both string and datetime end_time
                end_time = token.end_time
                if isinstance(end_time, str):
                    end_time = make_aware(parse_datetime(end_time))
                
                if end_time > buffer_time:
                    return token
                    
            return self._get_new_token()
        except Exception as e:
            logger.error(f"Error getting active token: {str(e)}")
            raise

    def _get_new_token(self):
        """Request new token with proper datetime handling"""
        try:
            seed = self._generate_seed()
            params = {
                'version': 0,
                'user': self.user,
                'seed': seed,
                'hours': self.token_expiry
            }

            params['sign'] = self._generate_signature(params, seed, token=None)
            params['sign_type'] = self.sign_type

            response = requests.post(
                f"{self.base_url}/interface?type=&action=get_verify_code",
                json=params,
                verify=True,
                timeout=20
            )

            data = response.json()
            if response.status_code == 200 and data.get('state') == 0:
                # Deactivate old token
                SmartPayToken.objects.filter(is_active=True).update(is_active=False)
                
                # Convert string timestamps to timezone-aware datetimes
                start_time = make_aware(parse_datetime(data['start_time']))
                end_time = make_aware(parse_datetime(data['end_time']))
                
                token = SmartPayToken.objects.create(
                    token=data['tokens'],
                    seed=data['seed'],
                    start_time=start_time,
                    end_time=end_time,
                    is_active=True
                )
                return token

            raise Exception(f"Failed to get new token: {data}")
        except Exception as e:
            logger.error(f"Error getting new token: {str(e)}")
            raise
    

    def _make_request(self, action, params, type_param="", retry_on_token_expiry=True):
        """Make API request with proper token handling"""
        try:
            if not self.current_token or self._is_token_expired(self.current_token):
                self.current_token = self._get_new_token()
            
            seed = self._generate_seed()
            base_params = {
                'version': 0,
                'user': self.user,
                'seed': seed,
            }

            base_params.update(params)            

            base_params['sign'] = self._generate_signature(base_params, seed, self.current_token)
            base_params['sign_type'] = self.sign_type
            
            print("here are the base params: ",base_params)

            response = requests.post(
                f"{self.base_url}/interface?type={type_param}&action={action}",
                json=base_params,
                verify=True,
                timeout=30
            )
            
            data = response.json()
            if response.status_code == 200:
                if retry_on_token_expiry and data.get('state') == -95131:  # Token expired
                    self.current_token = self._get_new_token()
                    return self._make_request(action, params, type_param, False)
                return data
                
            raise Exception(f"API request failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"Error making request to {action}: {str(e)}")
            raise
        
    def _is_token_expired(self, token):
        """Check if token is expired with proper datetime handling"""
        if isinstance(token.end_time, str):
            token.end_time = make_aware(parse_datetime(token.end_time))
        return token.end_time <= timezone.now()

    # Token Management
    def get_token(self):
        """Get current active token"""
        return self._get_active_token()
    
    # Account Management
    def get_account_details(self):
        """Get details of the account"""
        return self._make_request('accountdetail', {})
    
    def change_payment_password(self, new_password):
        """Change the Payment Password"""
        return self._make_request('changepwd', {'password': new_password})
    
    def transfer_amount(self, trans_id, recipient_value, amount):
        """Transfer to sub-agency or Point of Sales"""
        return self._make_request('transfer_amt', {
            'trans_id': trans_id,
            'rst_value': recipient_value,
            'amt': amount
        })
    
    # Prepayment Meter Functions
    def get_customer_details(self, meter_number):
        """Get the Details of Customer (prepayment)"""
        return self._make_request('get_cst_details', {'rst_value': meter_number}, 'ppe')
    
    def sell_power(self, trans_id, meter_number, amount, phone, channel='04', verify_code=''):
        """Sell the Power (prepayment)"""
        return self._make_request('sale', {
            'trans_id': trans_id,
            'rst_code': meter_number,
            'calc_mode': 'M',
            'amt': amount,
            'channel': channel,
            'phone': phone,
            'verify_code': verify_code or 'DONOTVERIFYDATA'
        }, 'ppe')
    
    def get_sale_details(self, transaction_code):
        """Get the details of selling the power (prepayment)"""
        return self._make_request('sales_trans_details', {'code': transaction_code}, 'ppe')
    
    def inquiry_sales_transactions(self, meter_number, count=5):
        """Inquiry the transactions of selling the power (prepayment)"""
        return self._make_request('search_sale_trans', {
            'rst_code': meter_number,
            'count': count
        }, 'ppe')
    
    def pay_arrear(self, trans_id, meter_number, amount, phone, channel='04', verify_code=''):
        """Pay the arrear (prepayment)"""
        return self._make_request('payarrear', {
            'trans_id': trans_id,
            'rst_code': meter_number,
            'amt': amount,
            'channel': channel,
            'phone': phone,
            'verify_code': verify_code or 'DONOTVERIFYDATA'
        }, 'ppe')
    
    def get_arrear_payment_details(self, transaction_code):
        """Get the details of Paying Arrear (Prepayment)"""
        return self._make_request('arrear_trans_details', {'trans_code': transaction_code}, 'ppe')
    
    def inquiry_arrear_transactions(self, meter_number):
        """Inquiry the transactions of paying the arrear (prepayment)"""
        return self._make_request('search_arear_trans', {'rst_code': meter_number}, 'ppe')


    # Post-payment Meter Functions
    def get_customer_bills(self, customer_reference):
        """Get the Bills of Customer (Post-Payment)"""
        return self._make_request('get_bills', {'rst_code': customer_reference}, 'pps')
    
    def get_bill_details(self, bill_code):
        """Get the details of bill (Post-Payment)"""
        return self._make_request('bill_details', {'rst_code': bill_code}, 'pps')
    
    def pay_bill(self, trans_id, bill_code, amount, phone, channel='04', verify_code=''):
        """Pay the bill (Post-Payment)"""
        return self._make_request('pay_bill', {
            'trans_id': trans_id,
            'rst_code': bill_code,
            'amt': amount,
            'channel': channel,
            'phone': phone,
            'verify_code': verify_code or 'DONOTVERIFYDATA'
        }, 'pps')
    
    def get_bill_transaction_details(self, transaction_code):
        """Get the details of Transaction (Post-Payment)"""
        return self._make_request('bill_trans_details', {'trans_code': transaction_code}, 'pps')
    
    def inquiry_bill_transactions(self, customer_reference):
        """Inquiry the transactions (Post payment)"""
        return self._make_request('search_bill_trans', {'rst_code': customer_reference}, 'pps')



