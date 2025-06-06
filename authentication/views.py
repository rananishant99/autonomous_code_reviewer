from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from .serializers import UserSignupSerializer
from rest_framework.response import Response
from rest_framework import status
from autonomous_code_reviewer.utils import create_api_response, create_serializer_response
from autonomous_code_reviewer.constants import ActionMessages
from .constants import Authentication

class UserSignupView(GenericAPIView):
    serializer_class = UserSignupSerializer
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return create_api_response(
                    status_code=status.HTTP_201_CREATED,
                    message=Authentication.SIGNUP['CREATED'],
                )
            return create_api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=create_serializer_response(serializer.errors),
            )
        except Exception as e:
            return create_api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ActionMessages.COMMON['SERVER_ERROR']
            )