from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators= [validate_password] )
    password_confirm= serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields= ['username', 'email', 'first_name', 'last_name', 
                 'password', 'password_confirm', 'phone', 'role']
        extra_kwargs = {
            'role': {'read_only': True}  # Role set by whoever creates the user
        }

    def validate(self,attrs):
        """Custom validation method.
        Called after individual field validation
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match!")

        attrs.pop('password_confirm', None)    #We remove this since it's not required for user creation
        return attrs
    
    def create(self, validated_data):
        """
        Create user with hashed password.
        """
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            role=validated_data.get('role', 'tenant')
        )
        return user
    
class UserSerializer(serializers.ModelSerializer):
    """Used to retrieve and update user data"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                 'phone', 'role', 'is_verified', 'created_at']
        read_only_fields = ['id','username','role','is_verified','created_at']


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    Notice we're not using ModelSerializer here since this is not tied to any specific model
    We're just validating credentials but not creating/updating a model 
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            if not user:
                raise serializers.ValidationError('Invalid Credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            attrs['user'] = user
            return attrs
        
        raise serializers.ValidationError('Must include username and password')


    