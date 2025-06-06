from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import serializers
from .constants import Authentication
from .models import GitToken

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(max_length=255)

    class Meta:
        model = User
        fields = ['email', 'password']

    def validate_email(self, value):
        # Ensure email is unique
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(Authentication.USER['EMAIL_EXISTS'])
        return value

    def create(self, validated_data):
        # Create user with email as username
        return User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password']
        )


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login with email and password."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)


class CustomRefreshTokenSerializer(serializers.Serializer):
    """Serializer to handle refresh token input for JWT refresh."""

    refresh_token = serializers.CharField(write_only=True)


class GitTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitToken
        fields = ['token']
        extra_kwargs = {
            'token': {'write_only': True}
        }