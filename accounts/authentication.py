from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    
    def authenticate(self, request): 
        cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'access_token')

        raw_token = request.COOKIES.get(cookie_name)
        
        if raw_token is None:
            # No token in cookie, then not authenticated, return none
            return None
        
        # Validate the token 
        validated_token = self.get_validated_token(raw_token)
        
        # Get user from validated token
        return self.get_user(validated_token), validated_token