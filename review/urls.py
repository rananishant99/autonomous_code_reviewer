from django.urls import path
from .views import (
    RepositoryListAPIView,
    RepositoryDetailAPIView,
    PullRequestListAPIView,
    PullRequestDetailAPIView,
    PRReviewAPIView,
    QuickReviewAPIView,
    CodeImprovementsAPIView,
    ReviewStatusAPIView,
    ReviewHistoryAPIView,
    ReviewDetailAPIView,
    HealthCheckAPIView,
)

urlpatterns = [
    # Health check
    path('health/', HealthCheckAPIView.as_view(), name='health-check'),
    
    # Repository endpoints
    path('repositories/', RepositoryListAPIView.as_view(), name='repository-list'),
    path('repositories/<str:owner>/<str:repo>/', RepositoryDetailAPIView.as_view(), name='repository-detail'),
    
    # Pull Request endpoints
    path('repositories/<str:owner>/<str:repo>/pulls/', PullRequestListAPIView.as_view(), name='pullrequest-list'),
    path('repositories/<str:owner>/<str:repo>/pulls/<int:pr_number>/', PullRequestDetailAPIView.as_view(), name='pullrequest-detail'),
    
    # Review endpoints
    path('review/', PRReviewAPIView.as_view(), name='pr-review'),
    path('review/quick/', QuickReviewAPIView.as_view(), name='quick-review'),
    path('review/<int:review_id>/status/', ReviewStatusAPIView.as_view(), name='review-status'),
    path('review/<int:review_id>/improvements/', CodeImprovementsAPIView.as_view(), name='code-improvements'),
    
    # Review management
    path('reviews/', ReviewHistoryAPIView.as_view(), name='review-history'),
    path('reviews/<int:review_id>/', ReviewDetailAPIView.as_view(), name='review-detail'),
]
