from rest_framework import serializers

class SmartPayRequestSerializer(serializers.Serializer):
    meter_number = serializers.CharField(required=False)
    customer_reference = serializers.CharField(required=False)
    bill_code = serializers.CharField(required=False)
    transaction_id = serializers.CharField(required=False)
    amount = serializers.DecimalField(
            max_digits=12,
            decimal_places=2,
            required=False,
            coerce_to_string=True  # Ensures amount is converted to string
        )    
    phone = serializers.CharField(required=False)
    transaction_code = serializers.CharField(required=False)
    channel = serializers.CharField(default='04')
    verify_code = serializers.CharField(required=False)
    count = serializers.IntegerField(default=5, required=False)
    new_password = serializers.CharField(required=False)
    recipient_value = serializers.CharField(required=False)


    def validate_amount(self, value):
        """Custom validation for amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value