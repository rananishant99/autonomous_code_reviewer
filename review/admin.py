from django.contrib import admin
from .models import ReviewRequest, ReviewResult, Repository, PullRequest


@admin.register(ReviewRequest)
class ReviewRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'repo', 'pr_number', 'status', 'user', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['owner', 'repo', 'pr_number', 'task_id']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    ordering = ['-created_at']


@admin.register(ReviewResult)
class ReviewResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'review_request', 'quality_score', 'created_at']
    list_filter = ['quality_score', 'created_at']
    search_fields = ['review_request__owner', 'review_request__repo', 'review_request__pr_number']
    readonly_fields = ['created_at']
    raw_id_fields = ['review_request']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('review_request', 'quality_score', 'created_at')
        }),
        ('Review Content', {
            'fields': ('overall_review', 'summary'),
            'classes': ('collapse',)
        }),
        ('Technical Details', {
            'fields': ('pr_details', 'file_reviews'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ['owner', 'name', 'language', 'stargazers_count', 'forks_count', 'private', 'updated_at']
    list_filter = ['language', 'private', 'updated_at', 'created_at']
    search_fields = ['owner', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    ordering = ['-updated_at']


@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'repository', 'user_login', 'state', 'additions', 'deletions', 'changed_files', 'draft', 'updated_at']
    list_filter = ['state', 'draft', 'updated_at', 'created_at']
    search_fields = ['title', 'body', 'user_login', 'repository__owner', 'repository__name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['repository']
    list_per_page = 25
    ordering = ['-updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('repository', 'number', 'title', 'user_login', 'state', 'draft')
        }),
        ('Content', {
            'fields': ('body', 'html_url'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('additions', 'deletions', 'changed_files'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )