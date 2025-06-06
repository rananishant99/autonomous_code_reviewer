from django.urls import path, include
from .views import UserSignupView, UserLoginView, CustomRefreshTokenView
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='user_signup'),
    path('login/', UserLoginView.as_view(), name='user_login'),
    path('token/refresh/', CustomRefreshTokenView.as_view(), name='token_refresh')

]