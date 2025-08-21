# import jwt
# from datetime import datetime, timedelta
# from django.conf import settings
# from django.contrib.auth import get_user_model
# from rest_framework import permissions
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from users.serializers import UserSerializer, LoginSerializer
# from rest_framework import status
# from rest_framework.exceptions import AuthenticationFailed


# User = get_user_model()


# from datetime import datetime, timedelta, timezone

# def get_token_for_user(user):
#     now = datetime.now(timezone.utc)  # UTC-aware current time

#     access_payload = {
#         'user_id': str(user.id),
#         'token_type': 'access',
#         'exp': now + timedelta(minutes=15),
#         'iat': now,
#     }
    
#     refresh_payload = {
#         'user_id': str(user.id),
#         'token_type': 'refresh',
#         'exp': now + timedelta(days=7),
#         'iat': now,
#     }
    
#     return {
#         'access': jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256'),
#         'refresh': jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256'),
#     }


# class LoginView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def post(self, request):
#         serializer = LoginSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.validated_data
        
#         tokens = get_token_for_user(user)
                
#         return Response({
#             'user': UserSerializer(user).data,
#             'access': tokens['access'],
#             'refresh': tokens['refresh']
#         })
    

# class RefreshTokenView(APIView):
#     def __init__(self, **kwargs):
#         self.now = datetime.now(timezone.utc)  # UTC-aware current time

#     permission_classes = [permissions.AllowAny]

#     def post(self, request):
#         refresh_token = request.data.get("refresh")
        
#         if not refresh_token:
#             return Response(
#                 {"detail": "Refresh token is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             payload = jwt.decode(
#                 refresh_token,
#                 settings.SECRET_KEY,
#                 algorithms=["HS256"]
#             )
            
#             # Verify it's a refresh token
#             if payload.get('token_type') != 'refresh':
#                 raise AuthenticationFailed("Invalid token type")
                
#             # Get the user
#             user_id = payload.get('user_id')
#             if not user_id:
#                 raise AuthenticationFailed("Invalid token payload")
                
#             user = User.objects.filter(id=user_id).first()
#             if not user:
#                 raise AuthenticationFailed("User not found")
            
#             # Generate new access token
#             new_access_payload = {
#                 'user_id': str(user.id),
#                 'token_type': 'access',
#                 'exp': self.now + timedelta(minutes=15),
#                 'iat': self.now,
#             }
#             new_access_token = jwt.encode(
#                 new_access_payload,
#                 settings.SECRET_KEY,
#                 algorithm='HS256'
#             )
            
#             return Response({
#                 'access': new_access_token
#             })
            
#         except jwt.ExpiredSignatureError:
#             return Response(
#                 {"detail": "Refresh token expired"},
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
#         except (jwt.InvalidTokenError, AuthenticationFailed) as e:
#             return Response(
#                 {"detail": str(e)},
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from users.serializers import UserSerializer, LoginSerializer

User = get_user_model()

def get_token_for_user(user):
    now = datetime.now(timezone.utc)

    access_payload = {
        'user_id': str(user.id),
        'token_type': 'access',
        'exp': now + timedelta(minutes=15),
        'iat': now,
    }
    
    refresh_payload = {
        'user_id': str(user.id),
        'token_type': 'refresh',
        'exp': now + timedelta(days=7),
        'iat': now,
    }
    
    return {
        'access': jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256'),
        'refresh': jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256'),
    }


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="User Login",
        description="Authenticate user and return JWT tokens",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Successful authentication",
                examples=[
                    OpenApiExample(
                        "Success Response",
                        value={
                            "user": {
                                "id": 1,
                                "username": "johndoe",
                                "email": "john@example.com",
                                "date_joined": "2024-01-01T00:00:00Z",
                                "is_active": True,
                                "is_staff": False
                            },
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Validation error",
                examples=[
                    OpenApiExample(
                        "Validation Error",
                        value={
                            "username": ["This field is required."],
                            "password": ["This field is required."]
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Authentication failed",
                examples=[
                    OpenApiExample(
                        "Invalid Credentials",
                        value={
                            "detail": "Invalid username or password"
                        }
                    )
                ]
            )
        },
        examples=[
            OpenApiExample(
                "Login Request",
                value={
                    "username": "johndoe",
                    "password": "securepassword123"
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        
        tokens = get_token_for_user(user)
                
        return Response({
            'user': UserSerializer(user).data,
            'access': tokens['access'],
            'refresh': tokens['refresh']
        })
    

class RefreshTokenView(APIView):
    permission_classes = [permissions.AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.now = datetime.now(timezone.utc)

    @extend_schema(
        tags=["Authentication"],
        summary="Refresh Access Token",
        description="Use refresh token to obtain a new access token",
        request=OpenApiTypes.OBJECT,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="New access token generated",
                examples=[
                    OpenApiExample(
                        "Success Response",
                        value={
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Bad request",
                examples=[
                    OpenApiExample(
                        "Missing Refresh Token",
                        value={
                            "detail": "Refresh token is required"
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Token validation failed",
                examples=[
                    OpenApiExample(
                        "Expired Token",
                        value={
                            "detail": "Refresh token expired"
                        }
                    ),
                    OpenApiExample(
                        "Invalid Token",
                        value={
                            "detail": "Invalid token"
                        }
                    ),
                    OpenApiExample(
                        "Wrong Token Type",
                        value={
                            "detail": "Invalid token type"
                        }
                    )
                ]
            )
        },
        examples=[
            OpenApiExample(
                "Refresh Token Request",
                value={
                    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")
        
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            
            # Verify it's a refresh token
            if payload.get('token_type') != 'refresh':
                raise AuthenticationFailed("Invalid token type")
                
            # Get the user
            user_id = payload.get('user_id')
            if not user_id:
                raise AuthenticationFailed("Invalid token payload")
                
            user = User.objects.filter(id=user_id).first()
            if not user:
                raise AuthenticationFailed("User not found")
            
            # Generate new access token
            new_access_payload = {
                'user_id': str(user.id),
                'token_type': 'access',
                'exp': self.now + timedelta(minutes=15),
                'iat': self.now,
            }
            new_access_token = jwt.encode(
                new_access_payload,
                settings.SECRET_KEY,
                algorithm='HS256'
            )
            
            return Response({
                'access': new_access_token
            })
            
        except jwt.ExpiredSignatureError:
            return Response(
                {"detail": "Refresh token expired"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except (jwt.InvalidTokenError, AuthenticationFailed) as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )