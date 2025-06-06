from django.urls import path, include
from .views import UserSignupView

urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='user_signup')
]