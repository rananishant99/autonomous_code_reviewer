from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from .serializers import UserSignupSerializer
from rest_framework.response import Response
from rest_framework import status

class UserSignupView(GenericAPIView):
    serializer_class = UserSignupSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "status": "success",
                "user_id": user.id,
                "email": user.email
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
