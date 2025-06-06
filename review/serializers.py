from rest_framework import serializers
from .models import ReviewRequest, ReviewResult, Repository, PullRequest

class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = '__all__'

class PullRequestSerializer(serializers.ModelSerializer):
    repository_name = serializers.CharField(source='repository.name', read_only=True)
    repository_owner = serializers.CharField(source='repository.owner', read_only=True)
    
    class Meta:
        model = PullRequest
        fields = '__all__'

class ReviewRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewRequest
        fields = '__all__'
        read_only_fields = ['id', 'status', 'task_id', 'created_at', 'updated_at']

class ReviewResultSerializer(serializers.ModelSerializer):
    review_request = ReviewRequestSerializer(read_only=True)
    
    class Meta:
        model = ReviewResult
        fields = '__all__'

class PRReviewInputSerializer(serializers.Serializer):
    owner = serializers.CharField(max_length=255)
    repo = serializers.CharField(max_length=255)
    pr_number = serializers.IntegerField()
    async_review = serializers.BooleanField(default=False)

class QuickReviewSerializer(serializers.Serializer):
    github_url = serializers.URLField()
    async_review = serializers.BooleanField(default=False)
    
    def validate_github_url(self, value):
        """Validate and parse GitHub PR URL"""
        import re
        pattern = r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
        match = re.match(pattern, value)
        if not match:
            raise serializers.ValidationError("Invalid GitHub PR URL format")
        return value

class CodeImprovementSerializer(serializers.Serializer):
    owner = serializers.CharField(max_length=255)
    repo = serializers.CharField(max_length=255)
    pr_number = serializers.IntegerField()
    file_path = serializers.CharField(max_length=500, required=False)