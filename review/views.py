from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import asyncio
import re
from datetime import datetime
from .models import Repository, PullRequest, ReviewRequest, ReviewResult
from .serializers import (
    RepositorySerializer, PullRequestSerializer, ReviewRequestSerializer,
    ReviewResultSerializer, PRReviewInputSerializer, QuickReviewSerializer,
    CodeImprovementSerializer
)
from .services import GitHubService, PRReviewService
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

class RepositoryListAPIView(APIView):
    """
    GET /api/repositories/
    List user's repositories with pagination
    """
    # authentication_classes = [JWTAuthentication]  # or your auth class
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            github_service = GitHubService(request.user)
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 20))
            
            repos_data = github_service.get_user_repositories(page=page, per_page=per_page)
            
            # Update or create repositories in database
            repositories = []
            for repo_data in repos_data:
                try:
                    # FIXED: Better data handling
                    repo_defaults = {
                        'description': repo_data.get('description') or '',
                        'html_url': repo_data.get('html_url', ''),
                        'language': repo_data.get('language') or '',
                        'stargazers_count': repo_data.get('stargazers_count', 0),
                        'forks_count': repo_data.get('forks_count', 0),
                        'open_issues_count': repo_data.get('open_issues_count', 0),
                        'private': repo_data.get('private', False),
                    }
                    
                    repo, created = Repository.objects.update_or_create(
                        owner=repo_data['owner']['login'],
                        name=repo_data['name'],
                        defaults=repo_defaults
                    )
                    repositories.append(repo)
                    
                except Exception as repo_error:
                    print(f"Error processing repo {repo_data.get('name', 'unknown')}: {repo_error}")
                    continue
            
            serializer = RepositorySerializer(repositories, many=True)
            
            return Response({
                'status': 'success',
                'count': len(repositories),
                'page': page,
                'data': serializer.data
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f"Failed to fetch repositories: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RepositoryDetailAPIView(APIView):
    """
    GET /api/repositories/{owner}/{repo}/
    Get specific repository details
    """
    
    def get(self, request, owner, repo):
        try:
            repository = get_object_or_404(Repository, owner=owner, name=repo)
            serializer = RepositorySerializer(repository)
            
            return Response({
                'status': 'success',
                'data': serializer.data
            })
            
        except Repository.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'Repository {owner}/{repo} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PullRequestListAPIView(APIView):
    """
    GET /api/repositories/{owner}/{repo}/pulls/
    List pull requests for a specific repository
    """
    
    def get(self, request, owner, repo):
        try:
            github_service = GitHubService(request.user)
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 20))
            state = request.query_params.get('state', 'open')
            
            prs_data = github_service.get_repository_prs(
                owner=owner, 
                repo=repo, 
                state=state, 
                page=page, 
                per_page=per_page
            )
            
            # Get or create repository with safe defaults
            repository, created = Repository.objects.get_or_create(
                owner=owner,
                name=repo,
                defaults={
                    'html_url': f'https://github.com/{owner}/{repo}',
                    'description': '',
                    'language': '',
                }
            )
            
            # Update or create pull requests in database
            pull_requests = []
            for pr_data in prs_data:
                try:
                    # FIXED: Better data handling for PRs
                    pr_defaults = {
                        'title': pr_data.get('title', '')[:500],  # Truncate if too long
                        'body': pr_data.get('body') or '',
                        'state': pr_data.get('state', 'open'),
                        'user_login': pr_data.get('user', {}).get('login', ''),
                        'html_url': pr_data.get('html_url', ''),
                        'additions': pr_data.get('additions', 0),
                        'deletions': pr_data.get('deletions', 0),
                        'changed_files': pr_data.get('changed_files', 0),
                        'draft': pr_data.get('draft', False),
                    }
                    
                    pr, created = PullRequest.objects.update_or_create(
                        repository=repository,
                        number=pr_data['number'],
                        defaults=pr_defaults
                    )
                    pull_requests.append(pr)
                    
                except Exception as pr_error:
                    print(f"Error processing PR #{pr_data.get('number', 'unknown')}: {pr_error}")
                    continue
            
            serializer = PullRequestSerializer(pull_requests, many=True)
            
            return Response({
                'status': 'success',
                'count': len(pull_requests),
                'page': page,
                'data': serializer.data
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f"Failed to fetch pull requests: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PullRequestDetailAPIView(APIView):
    """
    GET /api/repositories/{owner}/{repo}/pulls/{pr_number}/
    Get specific pull request details
    """
    
    def get(self, request, owner, repo, pr_number):
        try:
            github_service = GitHubService(request.user)
            pr_data = github_service.get_pr_details(owner, repo, pr_number)
            
            return Response({
                'status': 'success',
                'data': pr_data
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f"Failed to fetch PR details: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PRReviewAPIView(APIView):
    """
    POST /api/review/
    Start a PR review analysis
    """
    
    def post(self, request):
        serializer = PRReviewInputSerializer(data=request.data)
        if serializer.is_valid():
            owner = serializer.validated_data['owner']
            repo = serializer.validated_data['repo']
            pr_number = serializer.validated_data['pr_number']
            async_review = serializer.validated_data.get('async_review', False)
            
            try:
                # Create or get review request
                review_request, created = ReviewRequest.objects.get_or_create(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    defaults={'status': 'pending'}
                )
                
                if not created and review_request.status == 'completed':
                    # Return existing completed review
                    if hasattr(review_request, 'result'):
                        result_serializer = ReviewResultSerializer(review_request.result)
                        return Response({
                            'status': 'success',
                            'message': 'Review already completed',
                            'review_id': review_request.id,
                            'data': result_serializer.data
                        })
                
                if async_review:
                    # TODO: Implement Celery task for async processing
                    review_request.status = 'processing'
                    review_request.save()
                    
                    return Response({
                        'status': 'success',
                        'message': 'Review started asynchronously',
                        'review_id': review_request.id,
                        'task_id': review_request.task_id
                    })
                else:
                    # Synchronous review
                    review_service = PRReviewService(user=request.user)

                    
                    
                    # Update status to processing
                    review_request.status = 'processing'
                    review_request.save()
                    
                    async def run_review():
                        return await review_service.analyze_pr(owner, repo, pr_number)
                    
                    try:
                        result = asyncio.run(run_review())

                        # Optional: Log the structure to verify old_code/new_code are included
                        if result.get('file_reviews'):
                            print(f"\n🔍 DEBUGGING: Found {len(result['file_reviews'])} file reviews")
                            
                            for i, file_review in enumerate(result['file_reviews']):
                                print(f"\n📁 File {i+1}: {file_review.get('file', 'Unknown')}")
                                print(f"   Keys in file_review: {list(file_review.keys())}")
                                
                                if 'old_code' in file_review and 'new_code' in file_review:
                                    print(f"   ✅ Has separate old/new code")
                                    print(f"   📄 Old code length: {len(file_review['old_code'])} chars")
                                    print(f"   📄 New code length: {len(file_review['new_code'])} chars")
                                    
                                    # Show a snippet of the old/new code
                                    old_preview = file_review['old_code'][:100] + "..." if len(file_review['old_code']) > 100 else file_review['old_code']
                                    new_preview = file_review['new_code'][:100] + "..." if len(file_review['new_code']) > 100 else file_review['new_code']
                                    
                                    print(f"   📝 Old code preview: {repr(old_preview)}")
                                    print(f"   📝 New code preview: {repr(new_preview)}")
                                else:
                                    print(f"   ⚠️  Missing old/new code separation")
                                    print(f"   🔍 Available keys: {list(file_review.keys())}")
                        
                        # Save results - the database will automatically store the new fields
                        review_result, created = ReviewResult.objects.update_or_create(
                            review_request=review_request,
                            defaults={
                                'pr_details': result['pr_details'],
                                'overall_review': result['overall_review'],
                                'file_reviews': result['file_reviews'],  # This now includes old_code/new_code
                                'summary': result['summary'],
                            }
                        )
                        
                        review_request.status = 'completed'
                        review_request.save()
                        
                        return Response({
                            'status': 'success',
                            'message': 'Review completed',
                            'review_id': review_request.id,
                            'data': {
                                'pr_details': result['pr_details'],
                                'overall_review': result['overall_review'],
                                'file_reviews': result['file_reviews'],  # Now includes old_code/new_code for each file
                                'summary': result['summary'],
                            }
                        })
                        
                    except Exception as review_error:
                        review_request.status = 'failed'
                        review_request.error_message = str(review_error)  # Store error details
                        review_request.save()
                        
                        # Log the full error for debugging
                        print(f"❌ PR Review failed: {review_error}")
                        import traceback
                        print(traceback.format_exc())
                        
                        raise review_error
                    
            except Exception as e:
                return Response({
                    'status': 'error',
                    'message': f"Review failed: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class QuickReviewAPIView(APIView):
    """
    POST /api/review/quick/
    Quick review from GitHub URL
    """
    
    def post(self, request):
        serializer = QuickReviewSerializer(data=request.data)
        if serializer.is_valid():
            github_url = serializer.validated_data['github_url']
            async_review = serializer.validated_data.get('async_review', False)
            
            # Parse GitHub URL
            pattern = r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
            match = re.match(pattern, github_url)
            
            if not match:
                return Response({
                    'status': 'error',
                    'message': 'Invalid GitHub PR URL format. Expected: https://github.com/owner/repo/pull/123'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            owner, repo, pr_number = match.groups()
            pr_number = int(pr_number)
            
            # Create new request data
            review_data = {
                'owner': owner,
                'repo': repo,
                'pr_number': pr_number,
                'async_review': async_review
            }
            
            # Use the regular review endpoint
            request._full_data = review_data  # Store for use in PRReviewAPIView
            review_view = PRReviewAPIView()
            review_view.request = request
            
            # Create new serializer with parsed data
            review_serializer = PRReviewInputSerializer(data=review_data)
            if review_serializer.is_valid():
                request.data.update(review_data)
                return review_view.post(request)
            else:
                return Response({
                    'status': 'error',
                    'errors': review_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class CodeImprovementsAPIView(APIView):
    """
    GET /api/review/{review_id}/improvements/
    Get code improvements for a specific file or all files
    """
    
    def get(self, request, review_id):
        try:
            review_result = get_object_or_404(ReviewResult, review_request_id=review_id)
            file_path = request.query_params.get('file_path')
            
            if file_path:
                # Get improvements for specific file
                file_reviews = review_result.file_reviews
                file_improvement = None
                
                for file_review in file_reviews:
                    if file_review.get('file') == file_path:
                        file_improvement = file_review.get('improvements', 'No improvements available')
                        break
                
                if file_improvement:
                    return Response({
                        'status': 'success',
                        'file': file_path,
                        'improvements': file_improvement
                    })
                else:
                    return Response({
                        'status': 'error',
                        'message': f'File {file_path} not found in review'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                # Get improvements for all files
                improvements = {}
                for file_review in review_result.file_reviews:
                    file_name = file_review.get('file')
                    if file_name:
                        improvements[file_name] = {
                            'language': file_review.get('language'),
                            'improvements': file_review.get('improvements'),
                            'changes': file_review.get('changes')
                        }
                
                return Response({
                    'status': 'success',
                    'improvements': improvements
                })
                
        except ReviewResult.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'Review {review_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReviewStatusAPIView(APIView):
    """
    GET /api/review/{review_id}/status/
    Check the status of a review
    """
    
    def get(self, request, review_id):
        try:
            review_request = get_object_or_404(ReviewRequest, id=review_id)
            
            response_data = {
                'status': 'success',
                'review_id': review_id,
                'review_status': review_request.status,
                'created_at': review_request.created_at,
                'updated_at': review_request.updated_at,
                'owner': review_request.owner,
                'repo': review_request.repo,
                'pr_number': review_request.pr_number
            }
            
            # If review is completed, include results
            if review_request.status == 'completed' and hasattr(review_request, 'result'):
                response_data['result'] = ReviewResultSerializer(review_request.result).data
            
            return Response(response_data)
            
        except ReviewRequest.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'Review {review_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReviewHistoryAPIView(APIView):
    """
    GET /api/reviews/
    Get review history with pagination
    """
    
    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            per_page = min(int(request.query_params.get('per_page', 20)), 100)
            status_filter = request.query_params.get('status')
            
            reviews = ReviewRequest.objects.all()
            
            if status_filter:
                reviews = reviews.filter(status=status_filter)
            
            # Pagination
            start = (page - 1) * per_page
            end = start + per_page
            paginated_reviews = reviews[start:end]
            
            serializer = ReviewRequestSerializer(paginated_reviews, many=True)
            
            return Response({
                'status': 'success',
                'count': reviews.count(),
                'page': page,
                'per_page': per_page,
                'data': serializer.data
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReviewDetailAPIView(APIView):
    """
    GET /api/reviews/{review_id}/
    Get detailed review results
    DELETE /api/reviews/{review_id}/
    Delete a review
    """
    
    def get(self, request, review_id):
        try:
            review_request = get_object_or_404(ReviewRequest, id=review_id)
            
            if review_request.status == 'completed' and hasattr(review_request, 'result'):
                result_serializer = ReviewResultSerializer(review_request.result)
                return Response({
                    'status': 'success',
                    'data': result_serializer.data
                })
            else:
                request_serializer = ReviewRequestSerializer(review_request)
                return Response({
                    'status': 'success',
                    'data': request_serializer.data
                })
                
        except ReviewRequest.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'Review {review_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, review_id):
        try:
            review_request = get_object_or_404(ReviewRequest, id=review_id)
            review_request.delete()
            
            return Response({
                'status': 'success',
                'message': 'Review deleted successfully'
            })
            
        except ReviewRequest.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'Review {review_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HealthCheckAPIView(APIView):
    """
    GET /api/health/
    Health check endpoint
    """
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'service': 'PR Reviewer API',
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat()
        })