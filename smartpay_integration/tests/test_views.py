from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
import json

class SmartPayViewsTestCase(TestCase):
    def setUp(self):
        """Set up test data and client"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username='Alphonse',
            password='password'
        )

        self.client.force_authenticate(user=self.user)

        self.mock_token_response = {
            'token': '93847593304',
            'is_active': True,
            'start_time': '2025-08-19T22:00:00Z',
            'end_time': '2025-08-19T23:00:00Z'
        }

        self.mock_account_response = {
            'state': 0,
            'name': 'Account name',
            'accounts': [{'amount': 10000}]
        }

        self.mock_sale_response = {
            'state': 0,
            'trans_id': '39488484',
            'amount': 15000
        }

    def test_get_token_status(self):
        """Test successful token status retrieval"""
        # 1. Mocking the external service call
        with patch('smartpay_integration.services.smartpay_service.SmartPayService.get_token') as mock_get_token:
            # 2. Create a mock token object
            mock_token = MagicMock()
            mock_token.token = '93847593304'
            mock_token.is_active = True
            mock_token.start_time = '2025-08-19T22:00:00Z'
            mock_token.end_time = '2025-08-19T23:00:00Z'

            # 3. Configure the mock to return our faken token
            mock_get_token.return_value = mock_token

            # 4. Make the actual API call
            response = self.client.get(reverse('token-status'))

            # 5. Assertion - verify the response is correct
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('token', response.data)
            self.assertTrue(response.data['is_active'])

    def test_get_token_status_failure(self):
        """Test token status retrieval failure"""
        with patch('smartpay_integration.services.smartpay_service.SmartPayService.get_token') as mock_get_token:
            mock_get_token.side_effect = Exception('Token service unavailable')

            response = self.client.get(reverse('token-status'))

            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn('error', response.data)

    def test_get_account_details_success(self):
        """Test successful account details retrieval"""
        with patch('smartpay_integration.services.smartpay_service.SmartPayService.get_account_details') as mock_get_account:
            mock_get_account.return_value = self.mock_account_response
            
            response = self.client.post(reverse('account-details'))
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['state'], 0)
            self.assertEqual(response.data['name'], 'Account name')

    def test_sell_power(self):
        """Test successful power sale with various amount formats"""
        test_cases = [
            {'amount': 13567, 'expected': '13567.00'},      # Whole number
            {'amount': 2000.5, 'expected': '2000.50'},      # One decimal
            {'amount': 3544.44, 'expected': '3544.44'},    # Three decimals
            {'amount': '1000.99', 'expected': '1000.99'} # String input
        ]

        for test_case in test_cases:
            with self.subTest(amount=test_case['amount']):
                with patch('smartpay_integration.services.smartpay_service.SmartPayService.sell_power') as mock_sell:
                    mock_sell.return_value = self.mock_sale_response

                    payload = {
                        'transaction_id': 'TEST123',
                        'meter_number': '46000587157',
                        'amount': test_case['amount'],
                        'phone': '623040031',
                        'channel': '04',
                        'verify_code': 'DONOTVERIFYDATA'
                    }

                    response = self.client.post(
                        reverse('sell-power'),
                        data=json.dumps(payload),
                        content_type='application/json'
                    )

                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    # Verify service was called with formatted amount
                    mock_sell.assert_called_once()
                    call_args = mock_sell.call_args[1]
                    self.assertEqual(call_args['amount'], test_case['expected'])

    def test_sell_power_validation_error(self):
        """Test power sale with invalid data"""
        payload = {
            'transaction_id': '',  # Empty field
            'amount': -100,        # Negative amount
        }
        
        response = self.client.post(
            reverse('sell-power'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Debug: print what you're actually getting
        # print(f"Response status: {response.status_code}")
        # print(f"Response data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('transaction_id', response.data)
        self.assertIn('amount', response.data)


    def test_sell_power_service_error(self):
        """Test power sale when service fails"""
        with patch('smartpay_integration.services.smartpay_service.SmartPayService.sell_power') as mock_sell:
            mock_sell.side_effect = Exception('API unavailable')
            
            payload = {
                'transaction_id': 'TEST123',
                'meter_number': '46000587157',
                'amount': 15000,
                'phone': '623040031',
                'channel': '04'
            }
            
            response = self.client.post(
                reverse('sell-power'),
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn('error', response.data)

    def test_transfer_amount_success(self):
        """Test successful amount transfer"""
        with patch('smartpay_integration.services.smartpay_service.SmartPayService.transfer_amount') as mock_transfer:
            mock_transfer.return_value = {'state': 0, 'message': 'Transfer successful'}
            
            payload = {
                'transaction_id': 'TRANS123',
                'recipient_value': 'RECIPIENT001',
                'amount': 5000.00
            }
            
            response = self.client.post(
                reverse('transfer-amount'),
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_transfer.assert_called_once_with('TRANS123', 'RECIPIENT001', 5000.00)


    def test_get_customer_details_success(self):
        """Test successful customer details retrieval"""
        with patch('smartpay_integration.services.smartpay_service.SmartPayService.get_customer_details') as mock_get_customer:
            mock_response = {
                'state': 0,
                'name': 'John Doe',
                'device': '46000587157'
            }
            mock_get_customer.return_value = mock_response
            
            payload = {'meter_number': '46000587157'}
            
            response = self.client.post(
                reverse('customer-details'),
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['name'], 'John Doe')


    def test_pay_bill_amount_formatting(self):
        """Test bill payment amount formatting"""
        with patch('smartpay_integration.services.smartpay_service.SmartPayService.pay_bill') as mock_pay_bill:
            mock_pay_bill.return_value = {'state': 0, 'message': 'Bill paid'}
            
            test_amounts = [
                (1000, '1000.00'),
                (2500.5, '2500.50'),
                (3000.99, '3000.99')  # Rounded up
            ]
            
            for amount_input, expected_output in test_amounts:
                with self.subTest(amount=amount_input):
                    payload = {
                        'transaction_id': 'BILL123',
                        'bill_code': 'BILL001',
                        'amount': amount_input,
                        'phone': '623040031',
                        'verify_code': 'TESTCODE'
                    }
                    
                    response = self.client.post(
                        reverse('pay-bill'),
                        data=json.dumps(payload),
                        content_type='application/json'
                    )
                    
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    # Reset mock for next test
                    mock_pay_bill.reset_mock()

    def test_serializer_validation(self):
        """Test SmartPayRequestSerializer validation"""
        from smartpay_integration.serializers import SmartPayRequestSerializer
        
        # Test valid data
        valid_data = {
            'transaction_id': 'TEST123',
            'meter_number': '46000587157',
            'amount': '15000.00',
            'channel': '04'
        }
        serializer = SmartPayRequestSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())
        
        # Test invalid data
        invalid_data = {
            'transaction_id': '',  # Empty
            'amount': -100,        # Negative
            'channel': 'Invalid'   # Wrong format
        }
        serializer = SmartPayRequestSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('transaction_id', serializer.errors)
        self.assertIn('amount', serializer.errors)

    def test_error_logging(self):
        """Test that errors are properly logged"""
        import logging
        from unittest.mock import patch
        
        with patch('smartpay_integration.services.smartpay_service.SmartPayService.sell_power') as mock_sell, \
             patch('smartpay_integration.views.logger') as mock_logger:
            
            mock_sell.side_effect = Exception('Test error for logging')
            
            payload = {
                'transaction_id': 'TEST123',
                'meter_number': '46000587157',
                'amount': 15000,
                'phone': '623040031',
                'channel': '04'
            }
            
            response = self.client.post(
                reverse('sell-power'),
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            # Verify error was logged
            mock_logger.error.assert_called()
            self.assertIn('Test error for logging', mock_logger.error.call_args[0][0])
