from django.urls import path
from users.views import (LoginView, RefreshTokenView)

urlpatterns = [    
    # User authentication
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='token_refresh'),

]
