from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer, UserSerializer, LoginSerializer
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken
from django.conf import settings

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    """
    API endpoint for role based registration
    Registration rules:
    1. Landlords/Agents: Created via Django Admin only
    2.Caretakers: Created by landlords only
    3.Tenants: created by caretakers only

    This is to maintain business logic and prevent unauthorized account creation
    """

    queryset= User.objects.all()
    serializer_class=UserRegistrationSerializer
    permission_classes=[permissions.IsAuthenticated] # Must be logged in

    def create(self, request, *args, **kwargs):
        user = request.user
        requested_role= request.data.get('role','tenant')

        if requested_role == 'caretaker' and not user.is_landlord:
            return Response(
                {'error':'Only landlords can create caretaker accounts'},
                status=status.HTTP_403_FORBIDDEN
            )
        #Landlords and agents must be created via Django admin

        if requested_role in ['landlord','agent']:
            return Response(
                {'error':'Landlords and agents must be created by system admin'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        #proceed with user registration
        serializer = self.get_serializer(data= request.data)
        serializer.is_valid(raise_exception=True)

        new_user = serializer.save(role=requested_role)

        """
        We don't generate token yet. New user will login separately
        This follows the business logic flow: create accoint > send invitation > user sets password
        """

        return Response({
            'user': UserSerializer(new_user).data,
            'message': f"{requested_role.title()} account created successfully"
        }, status=status.HTTP_201_CREATED)
    
# @api_view(['POST'])
# @permission_classes([permissions.AllowAny])
# def login_view(request):

#     serializer = LoginSerializer(data=request.data, context={'request':request})

#     if serializer.is_valid():
#         user = serializer.validated_data['user']

#         #Generate JWT tokens
#         refresh = RefreshToken.for_user(user)

#         return Response({
#             'user': UserSerializer(user).data,
#             'refresh': str(refresh),
#             'access': str(refresh.access_token)
#         })
#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response({
            'user': UserSerializer(user).data,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)

        response.set_cookie(
            key=settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'),
            value=access_token,
            max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
            httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True),
            samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
        )

        response.set_cookie(
            key=settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
            value=refresh_token,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
            httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True),
            samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
        )

        return response

class LogoutView(generics.GenericAPIView):
    """ 
    Since tokens are stored in httpOnly cookies, JavaScript cannot delete them.
    This endpoint instructs the browser to delete the cookies by setting them
    with empty values and past expiry dates.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        
        response = Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)

        # Clear access token cookie
        response.delete_cookie(
            key=settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'),
            path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
             domain=settings.SIMPLE_JWT.get('AUTH_COOKIE_DOMAIN', None),
            samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
        )

        # Clear refresh token cookie
        response.delete_cookie(
            key=settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
            path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
             domain=settings.SIMPLE_JWT.get('AUTH_COOKIE_DOMAIN', None),
            samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
        )

        return response    
        
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class TokenRefreshView(BaseTokenRefreshView):
    
    def post(self, request, *args, **kwargs):
        
        refresh_token = request.COOKIES.get(
            settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token')
        )
        
        if refresh_token is None:
            return Response({
                'error': 'Refresh token not found in cookies'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        request.data['refresh'] = refresh_token
        
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Extract new access token from response
            access_token = response.data.get('access')
            new_response = Response({
                'message': 'Token refreshed successfully'
            }, status=status.HTTP_200_OK)

            new_response.set_cookie(
                key=settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'),
                value=access_token,
                max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
                httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True),
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
                path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
            )
            
            if 'refresh' in response.data:
                new_refresh_token = response.data.get('refresh')
                new_response.set_cookie(
                    key=settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
                    value=new_refresh_token,
                    max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
                    secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
                    httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True),
                    samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
                    path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
                )
            
            return new_response
        
        return response       