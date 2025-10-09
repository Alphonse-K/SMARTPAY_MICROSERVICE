from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from .services.smartpay_service import SmartPayService
from .serializers import SmartPayRequestSerializer
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from rest_framework.views import APIView
from smartpay_integration.models import APILog
from .services.utils import acquire_locks, release_locks
import time
from django.utils import timezone
from decimal import Decimal


logger = logging.getLogger(__name__)

class RootView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "Welcome to the API root"
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_token_status(request):
    """Check current token status"""
    try:
        service = SmartPayService()
        token = service.get_token()
        return Response({
            'token': token.token[:6] + '...',
            'is_active': token.is_active,
            'start_time': token.start_time,
            'end_time': token.end_time
        })
    except Exception as e:
        logger.error(f"Error getting token status: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Get account details",
    description="Retrieve account information including balances, account holder name, and account status.",
    tags=['Account Management'],
    responses={
        200: OpenApiResponse(
            description="Account details retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "name": {"type": "string", "example": "CASHMOOV"},
                    "accounts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "amt": {"type": "string", "example": "1975000.00"},
                                "currency": {"type": "string", "example": "GNF"}
                            }
                        }
                    }
                }
            }
        ),
        500: OpenApiResponse(description="Failed to retrieve account details")
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_account_details(request):
    """Get account details"""
    try:
        service = SmartPayService()
        result = service.get_account_details()
        return Response(result)
    except Exception as e:
        logger.error(f"Error getting account details: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Change payment password",
    description="Update the payment password for the SmartPay account.",
    tags=['Account Management'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Password changed successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "message": {"type": "string", "example": "Password updated successfully"}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid request data"),
        500: OpenApiResponse(description="Failed to change password")
    },
    examples=[
        OpenApiExample(
            "Valid Request",
            value={"new_password": "NewSecurePassword123!"},
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_payment_password(request):
    """Change payment password"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = SmartPayService()
        result = service.change_payment_password(serializer.validated_data['new_password'])
        return Response(result)
    except Exception as e:
        logger.error(f"Error changing payment password: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Transfer amount to sub-agency or POS",
    description="Transfer funds to a sub-agency or Point of Sales terminal.",
    tags=['Account Management'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Transfer completed successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "trans_id": {"type": "string", "example": "1234567890"},
                    "amount": {"type": "string", "example": "50000.00"},
                    "recipient": {"type": "string", "example": "POS001"}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid transfer request"),
        500: OpenApiResponse(description="Transfer failed")
    },
    examples=[
        OpenApiExample(
            "Transfer Request",
            value={
                "transaction_id": "TRANS123456",
                "recipient_value": "POS001",
                "amount": 50000.00
            },
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_amount(request):
    """Transfer to sub-agency or Point of Sales"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = SmartPayService()
        result = service.transfer_amount(
            serializer.validated_data['transaction_id'],
            serializer.validated_data['recipient_value'],
            serializer.validated_data['amount']
        )
        return Response(result)
    except Exception as e:
        logger.error(f"Error transferring amount: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Get customer details",
    description="Retrieve customer information for prepayment meters including account status, arrears, and consumption history.",
    tags=['Prepayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Customer details retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "name": {"type": "string", "example": "HAWA DIAKHABY"},
                    "device": {"type": "string", "example": "46000587157"},
                    "arrear_amt": {"type": "string", "example": "0.00"},
                    "buy_times": {"type": "string", "example": "362"}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid meter number"),
        500: OpenApiResponse(description="Failed to retrieve customer details")
    },
    examples=[
        OpenApiExample(
            "Customer Inquiry",
            value={"meter_number": "46000587157"},
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_customer_details(request):
    """Get customer details (prepayment)"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = SmartPayService()
        result = service.get_customer_details(serializer.validated_data['meter_number'])
        return Response(result)
    except Exception as e:
        logger.error(f"Error getting customer details: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Pre-payment Meter Functions

@extend_schema(
    summary="Sell electricity power",
    description="Process electricity power purchase for prepaid meters. Generates and activates electricity tokens.",
    tags=['Prepayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Power sale completed successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "trans_id": {"type": "string", "example": "7586689056677899"},
                    "kwh": {"type": "string", "example": "28.06"},
                    "tokens": {"type": "string", "example": "4465 0988 9012 0661 2849"},
                    "amt": {"type": "number", "example": 15000.00}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid sale request"),
        500: OpenApiResponse(description="Power sale failed")
    },
    examples=[
        OpenApiExample(
            "Power Sale Request",
            value={
                "transaction_id": "7586689056677899",
                "meter_number": "46000587157",
                "amount": 15000.00,
                "phone": "623040031",
                "channel": "04",
                "verify_code": "DONOTVERIFYDATA"
            },
            request_only=True
        )
    ]
)

def sanitize_for_json(data):
    """Convert any Decimals or non-serializable types recursively to JSON-safe objects."""
    if isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, dict):
        return {str(k): sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(i) for i in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_for_json(i) for i in data)
    else:
        return data


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sell_power(request):
    """Sell power with transaction locking and detailed logging."""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        APILog.objects.create(
            endpoint="sell_power_validation_error",
            request_data=sanitize_for_json(request.data),
            response_data=sanitize_for_json({"errors": serializer.errors}),
            status_code=400,
            duration=0.0
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    transaction_start = timezone.now()
    lock_keys = None

    try:
        transaction_id = serializer.validated_data['transaction_id']
        meter_number = serializer.validated_data['meter_number']
        amount_str = "{:.2f}".format(float(serializer.validated_data['amount']))

        lock_keys, error_message = acquire_locks(
            transaction_id, meter_number, amount_str, "sell_power"
        )

        if error_message:
            APILog.objects.create(
                endpoint="sell_power",
                request_data=sanitize_for_json(serializer.validated_data),
                response_data=sanitize_for_json({"error": error_message}),
                status_code=423,
                duration=(timezone.now() - transaction_start).total_seconds()
            )
            return Response({'error': error_message}, status=status.HTTP_423_LOCKED)

        service = SmartPayService()
        service_start = time.time()
        result = service.sell_power(
            trans_id=transaction_id,
            meter_number=meter_number,
            amount=amount_str,
            phone=serializer.validated_data['phone'],
            channel=serializer.validated_data['channel'],
            verify_code=serializer.validated_data.get('verify_code', '')
        )
        service_duration = time.time() - service_start

        # Convert everything safely
        safe_result = sanitize_for_json(result)

        APILog.objects.create(
            endpoint="sell_power",
            request_data=sanitize_for_json(serializer.validated_data),
            response_data=safe_result,
            status_code=200,
            duration=(timezone.now() - transaction_start).total_seconds()
        )

        return Response(safe_result, status=status.HTTP_200_OK)

    except Exception as e:
        APILog.objects.create(
            endpoint="sell_power",
            request_data=sanitize_for_json(serializer.validated_data),
            response_data=sanitize_for_json({"error": str(e)}),
            status_code=500,
            duration=(timezone.now() - transaction_start).total_seconds()
        )

        logger.error(f"Error selling power: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        release_locks(lock_keys)


@extend_schema(
    summary="Get sale details",
    description="Retrieve detailed information about a specific power sale transaction.",
    tags=['Prepayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Sale details retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "trans_id": {"type": "string", "example": "7586689056677899"},
                    "kwh": {"type": "string", "example": "28.06"},
                    "trans_time": {"type": "string", "format": "date-time", "example": "2025-08-18 13:07:43"}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid transaction code"),
        500: OpenApiResponse(description="Failed to retrieve sale details")
    },
    examples=[
        OpenApiExample(
            "Sale Details Request",
            value={"transaction_code": "00000250818130743721"},
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_sale_details(request):
    """Get sale details (prepayment)"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        service = SmartPayService()
        result = service.get_sale_details(
            transaction_code=serializer.validated_data['transaction_code']
        )
        return Response(result)
    except Exception as e:
        logger.error(f"Error getting sale details: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Inquiry sales transactions",
    description="Retrieve a list of recent power sale transactions for a specific meter.",
    tags=['Prepayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Sales transactions retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "details": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "trans_id": {"type": "string", "example": "7586689056677899"},
                                "amount": {"type": "string", "example": "15000.00"},
                                "trans_time": {"type": "string", "format": "date-time", "example": "2025-08-18 13:07:43"}
                            }
                        }
                    }
                }
            }
        ),
        400: OpenApiResponse(description="Invalid request parameters"),
        500: OpenApiResponse(description="Failed to retrieve transactions")
    },
    examples=[
        OpenApiExample(
            "Sales Inquiry Request",
            value={
                "meter_number": "46000587157",
                "count": 5
            },
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def inquiry_sales_transactions(request):
    """Inquiry the transactions of selling the power (prepayment)"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = SmartPayService()
        result = service.inquiry_sales_transactions(
            meter_number=serializer.validated_data['meter_number'],
            count=serializer.validated_data['count']
        )
        result["details"] = result['details'][:request.data['count']]
        return Response(result)
    except Exception as e:
        logger.error(f"Error getting transactions inquiry: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Pay electricity arrear",
    description="Process payment for outstanding electricity arrears on a prepaid meter.",
    tags=['Prepayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Arrear payment completed successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "trans_id": {"type": "string", "example": "ARR123456789"},
                    "arrear_amt": {"type": "string", "example": "7500.00"},
                    "paid_amt": {"type": "string", "example": "7500.00"}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid payment request"),
        500: OpenApiResponse(description="Arrear payment failed")
    },
    examples=[
        OpenApiExample(
            "Arrear Payment Request",
            value={
                "transaction_id": "ARR123456789",
                "meter_number": "46000587157",
                "amount": 7500.00,
                "phone": "623040031",
                "verify_code": "VERIFY123"
            },
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_arrear(request):
    """Pay the arrear (prepayment)"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = SmartPayService()
        amount = "{:.2f}".format(float(serializer.validated_data['amount']))
        result = service.pay_arrear(
            trans_id=serializer.validated_data['transaction_id'],
            meter_number=serializer.validated_data['meter_number'],
            amount=amount,
            phone=serializer.validated_data['phone'],
            verify_code=serializer.validated_data['verify_code']          
        )
        return Response(result)
    except Exception as e:
        logger.error(f"Error paying the arrear: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Get arrear payment details",
    description="Retrieve detailed information about a specific arrear payment transaction.",
    tags=['Prepayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Arrear payment details retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "trans_id": {"type": "string", "example": "ARR123456789"},
                    "arrear_amt": {"type": "string", "example": "7500.00"},
                    "paid_amt": {"type": "string", "example": "7500.00"}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid transaction code"),
        500: OpenApiResponse(description="Failed to retrieve payment details")
    },
    examples=[
        OpenApiExample(
            "Arrear Details Request",
            value={"transaction_code": "ARR123456789"},
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_arrear_payment_details(request):
    """Get the details of Paying Arrear (Prepayment)"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        service = SmartPayService()
        result = service.get_arrear_payment_details(
            transaction_code=serializer.validated_data['transaction_code']
        )
        return Response(result)
    except Exception as e:
        logger.error(f"Error getting details of arrear payment: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Inquiry arrear transactions",
    description="Retrieve a list of recent arrear payment transactions for a specific meter.",
    tags=['Prepayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Arrear transactions retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "details": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "trans_id": {"type": "string", "example": "ARR123456789"},
                                "amount": {"type": "string", "example": "7500.00"},
                                "trans_time": {"type": "string", "format": "date-time", "example": "2025-08-18 13:07:43"}
                            }
                        }
                    }
                }
            }
        ),
        400: OpenApiResponse(description="Invalid meter number"),
        500: OpenApiResponse(description="Failed to retrieve arrear transactions")
    },
    examples=[
        OpenApiExample(
            "Arrear Inquiry Request",
            value={"meter_number": "46000587157"},
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def inquiry_arrear_transactions(request):
    """Inquiry the transactions of paying the arrear (prepayment)"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = SmartPayService()
        result = service.inquiry_arrear_transactions(
            meter_number=serializer.validated_data['meter_number']
        )
        return Response(result)
    except Exception as e:
        logger.error(f"Error getting transactions inquiry for arrear payment: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Post-payment Meter Functions

@extend_schema(
    summary="Get customer bills",
    description="Retrieve all outstanding bills for a postpaid customer.",
    tags=['Postpayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Customer bills retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "bills": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "bill_code": {"type": "string", "example": "BILL001"},
                                "amount": {"type": "string", "example": "25000.00"},
                                "due_date": {"type": "string", "format": "date", "example": "2025-09-01"}
                            }
                        }
                    }
                }
            }
        ),
        400: OpenApiResponse(description="Invalid customer reference"),
        500: OpenApiResponse(description="Failed to retrieve customer bills")
    },
    examples=[
        OpenApiExample(
            "Bills Request",
            value={"customer_reference": "CUST123456"},
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_customer_bills(request):
    """Get the Bills of Customer (Post-Payment)"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = SmartPayService()
        result = service.get_customer_bills(
            customer_reference=serializer.validated_data['customer_reference']
        )
        return Response(result)
    except Exception as e:
        logger.error(f"Error getting the bills of customer (Post-Payment): {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Get bill details",
    description="Retrieve detailed information about a specific electricity bill.",
    tags=['Postpayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Bill details retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "bill_code": {"type": "string", "example": "BILL001"},
                    "amount": {"type": "string", "example": "25000.00"},
                    "consumption": {"type": "string", "example": "150.25 kWh"}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid bill code"),
        500: OpenApiResponse(description="Failed to retrieve bill details")
    },
    examples=[
        OpenApiExample(
            "Bill Details Request",
            value={"bill_code": "BILL001"},
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_bill_details(request):
    """Get the details of bill (Post-Payment)"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = SmartPayService()
        result = service.get_bill_details(
            bill_code=serializer.validated_data['bill_code']
        )
        return Response(result)
    except Exception as e:
        logger.error(f"Error getting the details of the bill: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Pay electricity bill",
    description="Process payment for an outstanding electricity bill for postpaid customers.",
    tags=['Postpayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Bill payment completed successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "trans_id": {"type": "string", "example": "BILLPAY123456"},
                    "bill_code": {"type": "string", "example": "BILL001"},
                    "paid_amt": {"type": "string", "example": "25000.00"}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid payment request"),
        500: OpenApiResponse(description="Bill payment failed")
    },
    examples=[
        OpenApiExample(
            "Bill Payment Request",
            value={
                "transaction_id": "BILLPAY123456",
                "bill_code": "BILL001",
                "amount": 25000.00,
                "phone": "623040031",
                "verify_code": "VERIFY123"
            },
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_bill(request):
    """Pay the bill (Post-Payment) with double locking and transaction logging"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    transaction_start = timezone.now()
    lock_keys = None
    
    try:
        # Extract data
        transaction_id = serializer.validated_data['transaction_id']
        bill_code = serializer.validated_data['bill_code']
        amount_str = "{:.2f}".format(float(serializer.validated_data['amount']))
        phone = serializer.validated_data['phone']
        verify_code = serializer.validated_data['verify_code']
        
        # Acquire both locks
        lock_keys, error_message = acquire_locks(
            transaction_id, bill_code, amount_str, "pay_bill"
        )
        
        if error_message:
            # Log the lock failure
            APILog.objects.create(
                endpoint="pay_bill",
                request_data=serializer.validated_data,
                response_data={"error": error_message},
                status_code=423,
                duration=0.0
            )
            return Response(
                {'error': error_message},
                status=status.HTTP_423_LOCKED
            )
        
        # Process the transaction
        service_start_time = time.time()
        service = SmartPayService()
        result = service.pay_bill(
            trans_id=transaction_id,
            bill_code=bill_code,
            amount=amount_str,
            phone=phone,
            verify_code=verify_code
        )
        service_duration = time.time() - service_start_time
        
        # Log successful transaction
        APILog.objects.create(
            endpoint="pay_bill_success",
            request_data={
                'transaction_id': transaction_id,
                'bill_code': bill_code,
                'amount': amount_str,
                'phone': phone,
                'verify_code': verify_code
            },
            response_data=result,
            status_code=200,
            duration=service_duration
        )
        
        return Response(result)
        
    except Exception as e:
        # Log the error
        error_duration = (timezone.now() - transaction_start).total_seconds()
        APILog.objects.create(
            endpoint="pay_bill",
            request_data=serializer.validated_data if serializer.is_valid() else request.data,
            response_data={"error": str(e)},
            status_code=500,
            duration=error_duration
        )
        
        logger.error(f"Error paying bill: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
    finally:
        # Always release locks
        release_locks(lock_keys)
    
@extend_schema(
    summary="Get bill transaction details",
    description="Retrieve detailed information about a specific bill payment transaction.",
    tags=['Postpayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Transaction details retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "trans_id": {"type": "string", "example": "BILLPAY123456"},
                    "bill_code": {"type": "string", "example": "BILL001"},
                    "paid_amt": {"type": "string", "example": "25000.00"}
                }
            }
        ),
        400: OpenApiResponse(description="Invalid transaction code"),
        500: OpenApiResponse(description="Failed to retrieve transaction details")
    },
    examples=[
        OpenApiExample(
            "Transaction Details Request",
            value={"transaction_code": "BILLPAY123456"},
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_bill_transaction_details(request):
     """Get the details of Transaction (Post-Payment)"""
     serializer = SmartPayRequestSerializer(data=request.data)
     if not serializer.is_valid():
         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
     
     try:
         service = SmartPayService()
         result = service.get_bill_transaction_details(
             transaction_code=serializer.validated_data['transaction_code']
         )
         return Response(result)
     except Exception as e:
        logger.error(f"Error getting details of transaction (Post-Payment): {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    summary="Inquiry bill transactions",
    description="Retrieve a list of recent bill payment transactions for a specific customer.",
    tags=['Postpayment'],
    request=SmartPayRequestSerializer,
    responses={
        200: OpenApiResponse(
            description="Bill transactions retrieved successfully",
            response={
                "type": "object",
                "properties": {
                    "state": {"type": "integer", "example": 0},
                    "transactions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "trans_id": {"type": "string", "example": "BILLPAY123456"},
                                "amount": {"type": "string", "example": "25000.00"},
                                "trans_time": {"type": "string", "format": "date-time", "example": "2025-08-18 13:07:43"}
                            }
                        }
                    }
                }
            }
        ),
        400: OpenApiResponse(description="Invalid customer reference"),
        500: OpenApiResponse(description="Failed to retrieve bill transactions")
    },
    examples=[
        OpenApiExample(
            "Bill Transactions Inquiry",
            value={"customer_reference": "CUST123456"},
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def inquiry_bill_transactions(request):
    """Inquiry the transactions (Post payment)"""
    serializer = SmartPayRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = SmartPayService()
        result = service.inquiry_bill_transactions(
            customer_reference=serializer.validated_data['customer_reference']
        )
        return Response(result)
    except Exception as e:
        logger.error(f"Error getting inquiry of transaction (Post-Payment): {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
