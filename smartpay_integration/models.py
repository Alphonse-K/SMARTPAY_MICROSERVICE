from django.db import models


class SmartPayToken(models.Model):
    token = models.CharField(max_length=32)
    seed = models.CharField(max_length=32)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'smartpay_token'
        indexes = [
            models.Index(fields=['is_active', 'end_time'])
        ]

    def __str__(self):
        return f"Token {self.token[:6]} (Active: {self.is_active})"
    

class APILog(models.Model):
    endpoint = models.CharField(max_length=255)
    request_data = models.JSONField()
    response_data = models.JSONField()
    status_code = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    duration = models.FloatField(help_text='Duration in seconds')

    class Meta:
        db_table = 'api_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.endpoint} - {self.status_code} - {self.created_at}"

