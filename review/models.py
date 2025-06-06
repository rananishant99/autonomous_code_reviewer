
from django.db import models
from django.contrib.auth.models import User
import json

class ReviewRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.AutoField(primary_key=True)
    owner = models.CharField(max_length=255)
    repo = models.CharField(max_length=255)
    pr_number = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    task_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        unique_together = ['owner', 'repo', 'pr_number']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.owner}/{self.repo} PR #{self.pr_number}"

class ReviewResult(models.Model):
    review_request = models.OneToOneField(ReviewRequest, on_delete=models.CASCADE, related_name='result')
    pr_details = models.JSONField(default=dict)
    overall_review = models.TextField(default='')
    file_reviews = models.JSONField(default=list)
    summary = models.TextField(default='')
    quality_score = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review for {self.review_request}"

class Repository(models.Model):
    owner = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')  # FIXED: Added default
    html_url = models.URLField(default='')  # FIXED: Added default
    language = models.CharField(max_length=100, blank=True, default='')  # FIXED: Added default
    stargazers_count = models.IntegerField(default=0)
    forks_count = models.IntegerField(default=0)
    open_issues_count = models.IntegerField(default=0)
    private = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)  # FIXED: auto_now instead of manual
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['owner', 'name']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.owner}/{self.name}"

class PullRequest(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='pull_requests')
    number = models.IntegerField()
    title = models.CharField(max_length=500, default='')  # FIXED: Added default
    body = models.TextField(blank=True, default='')  # FIXED: Added default
    state = models.CharField(max_length=20, default='open')  # FIXED: Added default
    user_login = models.CharField(max_length=255, default='')  # FIXED: Added default
    html_url = models.URLField(default='')  # FIXED: Added default
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    changed_files = models.IntegerField(default=0)
    draft = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)  # FIXED: auto_now_add
    updated_at = models.DateTimeField(auto_now=True)  # FIXED: auto_now
    
    class Meta:
        unique_together = ['repository', 'number']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"PR #{self.number}: {self.title}"