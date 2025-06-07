from django.contrib import admin
from .models import ChatSession, ChatMessage, ConversationSummary, UserPreference, AgentUsageStats, GuardrailsLog

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'message_count', 'memory_enabled', 'last_agent_used', 'created_at']
    list_filter = ['memory_enabled', 'last_agent_used', 'created_at']
    search_fields = ['session_id', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'duration']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'agent_used', 'is_guardrails_blocked', 'has_code', 'user_rating', 'timestamp']
    list_filter = ['agent_used', 'is_guardrails_blocked', 'has_code', 'user_rating', 'timestamp']
    search_fields = ['user_message', 'bot_response']
    readonly_fields = ['timestamp']

@admin.register(ConversationSummary)
class ConversationSummaryAdmin(admin.ModelAdmin):
    list_display = ['session', 'generated_at', 'token_count']
    search_fields = ['summary', 'key_topics', 'technologies_mentioned']
    readonly_fields = ['generated_at']

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'default_memory_enabled', 'preferred_agent', 'strict_guardrails']
    list_filter = ['default_memory_enabled', 'preferred_agent', 'strict_guardrails']

@admin.register(AgentUsageStats)
class AgentUsageStatsAdmin(admin.ModelAdmin):
    list_display = ['agent_name', 'date', 'usage_count', 'success_rate', 'avg_response_time_ms']
    list_filter = ['agent_name', 'date']
    readonly_fields = ['success_rate']

@admin.register(GuardrailsLog)
class GuardrailsLogAdmin(admin.ModelAdmin):
    list_display = ['blocked_query', 'query_category', 'timestamp']
    list_filter = ['query_category', 'timestamp']
    search_fields = ['blocked_query', 'classification_reason']
    readonly_fields = ['timestamp']