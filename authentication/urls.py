from django.urls import path, include
from .views import UserSignupView, UserLoginView, CustomRefreshTokenView, SaveGitHubTokenView


urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='user_signup'),
    path('login/', UserLoginView.as_view(), name='user_login'),
    path('token/refresh/', CustomRefreshTokenView.as_view(), name='token_refresh'),
    path('save-github-token/', SaveGitHubTokenView.as_view(), name='save_github_token'),

]