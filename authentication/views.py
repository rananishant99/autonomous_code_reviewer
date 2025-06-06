from rest_framework import status, serializers
from rest_framework.generics import GenericAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate

from autonomous_code_reviewer.utils import (
    create_api_response,
    create_serializer_response,
)
from autonomous_code_reviewer.constants import ActionMessages

from .serializers import UserSignupSerializer, UserLoginSerializer, CustomRefreshTokenSerializer, GitTokenSerializer
from .constants import Authentication
from .models import GitToken

class UserSignupView(GenericAPIView):
    serializer_class = UserSignupSerializer
    permission_classes = [AllowAny] 

    def post(self, request, *args, **kwargs):
        """
        Handles user signup.
        Validates and saves user data.
        """
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return create_api_response(
                    status_code=status.HTTP_201_CREATED,
                    message=Authentication.SIGNUP['CREATED'],
                )
            # Return validation errors
            return create_api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=create_serializer_response(serializer.errors),
            )
        except Exception:
            # Catch server-side exceptions
            return create_api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ActionMessages.COMMON['SERVER_ERROR']
            )


class UserLoginView(GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny] 

    def post(self, request, *args, **kwargs):
        """
        Handles user login.
        Validates credentials and returns JWT tokens.
        """
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                data = serializer.validated_data

                # Authenticate user using email and password
                user = authenticate(username=data['email'], password=data['password'])
                if not user:
                    return create_api_response(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message=Authentication.LOGIN['NOT_FOUND'],
                    )

                # Generate access and refresh tokens
                refresh = RefreshToken.for_user(user)
                token_data = {
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                }

                return create_api_response(
                    status_code=status.HTTP_200_OK,
                    message=Authentication.LOGIN['LOGIN'],
                    data=token_data
                )

            # Return serializer validation errors
            return create_api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=create_serializer_response(serializer.errors),
            )
        except Exception:
            # Catch server-side exceptions
            return create_api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ActionMessages.COMMON['SERVER_ERROR']
            )


class CustomRefreshTokenView(GenericAPIView):
    serializer_class = CustomRefreshTokenSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Handles refresh token.
        Validates refresh token and returns new access token.
        """
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                refresh_token = serializer.validated_data['refresh_token']

                try:
                    refresh = RefreshToken(refresh_token)
                except Exception:
                    return create_api_response(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="Invalid refresh token"
                    )

                access_token = str(refresh.access_token)

                return create_api_response(
                    status_code=status.HTTP_200_OK,
                    message="Access token generated successfully",
                    data={"access_token": access_token}
                )
            
            # Return validation errors
            return create_api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=create_serializer_response(serializer.errors)
            )

        except Exception:
            return create_api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error"
            )


class SaveGitHubTokenView(GenericAPIView):
    """
    API to receive a GitHub token and save it for the authenticated user.
    """
    serializer_class = GitTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            token_value = serializer.validated_data['token']
            token_obj, created = GitToken.objects.update_or_create(
                user=request.user,
                defaults={'token': token_value}
            )
            return create_api_response(
                status_code=status.HTTP_200_OK,
                message=(
                    Authentication.GITHUB['UPDATED'] if not created else Authentication.GITHUB['CREATED']
                )
            )
        # Return validation errors
        return create_api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=create_serializer_response(serializer.errors)
        )