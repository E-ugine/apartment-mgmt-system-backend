from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer, UserSerializer, LoginSerializer

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    """
    API endpoint for role based registration
    Registration rules:
    1. Landlords: Created by superuser only
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
    
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):

    serializer = LoginSerializer(data=request.data, context={'request':request})

    if serializer.is_valid():
        user = serializer.validated_data['user']

        #Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    View and update user profile
    RetrieveUpdateView handles Get(retrieve) and PUT/PATCH(update) with its built-in pernmission checking
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        #return the current user
        return self.request.user   
