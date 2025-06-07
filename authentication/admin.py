from django.contrib import admin
from .models import GitToken
# Register your models here.

@admin.register(GitToken)
class GitTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at')
    search_fields = ('user__username', 'token')
    list_filter = ('created_at',)