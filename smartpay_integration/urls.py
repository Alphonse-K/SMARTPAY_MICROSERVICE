from django.urls import path
from smartpay_integration.views import (
    # get_token_status,
    get_account_details,
    change_payment_password,
    transfer_amount,
    get_customer_details,
    sell_power,
    get_sale_details,
    inquiry_sales_transactions,
    pay_arrear,
    get_arrear_payment_details,
    inquiry_arrear_transactions,
    get_customer_bills,
    get_bill_details,
    pay_bill,
    get_bill_transaction_details,
    inquiry_bill_transactions,
)

urlpatterns = [

    # Token Management
    # path('token/status/', get_token_status, name='token-status'),
    
    # Account Management
    path('account/details/', get_account_details, name='account-details'),
    path('account/change-password/', change_payment_password, name='change-password'),
    path('account/transfer/', transfer_amount, name='transfer-amount'),
    path('account/customer-details/', get_customer_details, name='customer-details'),
    
    # Prepayment Meter Endpoints
    path('prepayment/customer/details/', get_customer_details, name='prepayment-customer-details'),
    path('prepayment/sell/', sell_power, name='sell-power'),
    path('prepayment/sale/details/', get_sale_details, name='sale-details'),
    path('prepayment/sales/inquiry/', inquiry_sales_transactions, name='sales-inquiry'),
    path('prepayment/arrear/pay/', pay_arrear, name='pay-arrear'),
    path('prepayment/arrear/details/', get_arrear_payment_details, name='arrear-details'),
    path('prepayment/arrear/inquiry/', inquiry_arrear_transactions, name='arrear-inquiry'),
    
    # # Post-payment Meter Endpoints
    path('postpayment/bills/', get_customer_bills, name='customer-bills'),
    path('postpayment/bill/details/', get_bill_details, name='bill-details'),
    path('postpayment/bill/pay/', pay_bill, name='pay-bill'),
    path('postpayment/bill/transaction/details/', get_bill_transaction_details, name='bill-transaction-details'),
    path('postpayment/bill/transactions/inquiry/', inquiry_bill_transactions, name='bill-transactions-inquiry'),
]
