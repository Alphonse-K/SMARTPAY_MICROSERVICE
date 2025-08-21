from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication
from django.core.cache import cache
from users.models import User
import jwt
from config import settings


class SimpleJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        try:
            token = auth_header.split(" ")[1]
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=["HS256"],
                options={
                    'verify_exp': True,
                    'verify_iss': True,
                    'verify_aud': True,
                }
            )
            
            # Additional payload validation
            if payload.get('token_type') != 'access':
                raise AuthenticationFailed('Invalid token type', code='invalid_token_type')
                
            # Cache user to reduce DB hits
            user_id = payload["user_id"]
            cache_key = f"user_{user_id}"
            user = cache.get(cache_key)
            
            if not user:
                user = User.objects.filter(id=user_id).first()
                if not user:
                    raise AuthenticationFailed('User not found', code='user_not_found')
                cache.set(cache_key, user, timeout=300)
                
            return (user, None)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expired', code='token_expired')
        except (jwt.InvalidTokenError, KeyError) as e:
            raise AuthenticationFailed('Invalid token', code='invalid_token')
