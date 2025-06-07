# chatbot/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class ChatSession(models.Model):
    """Enhanced chat session model with memory tracking"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Memory and session metadata
    memory_enabled = models.BooleanField(default=True)
    last_agent_used = models.CharField(max_length=50, blank=True)
    session_context = models.TextField(blank=True, help_text="Additional session context")
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Session {self.session_id} - {self.user or 'Anonymous'}"
    
    @property
    def message_count(self):
        return self.messages.count()
    
    @property
    def coding_message_count(self):
        return self.messages.exclude(agent_used='guardrails_blocked').count()
    
    @property
    def blocked_message_count(self):
        return self.messages.filter(agent_used='guardrails_blocked').count()
    
    @property
    def duration(self):
        return self.updated_at - self.created_at
    
    @property
    def agents_used(self):
        return list(self.messages.exclude(
            agent_used='guardrails_blocked'
        ).values_list('agent_used', flat=True).distinct())

class ChatMessage(models.Model):
    """Enhanced chat message model with metadata"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    user_message = models.TextField()
    bot_response = models.TextField()
    agent_used = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Enhanced metadata
    is_guardrails_blocked = models.BooleanField(default=False)
    response_time_ms = models.IntegerField(null=True, blank=True, help_text="Response time in milliseconds")
    token_count = models.IntegerField(null=True, blank=True, help_text="Estimated token count")
    has_code = models.BooleanField(default=False, help_text="Whether response contains code")
    user_rating = models.IntegerField(null=True, blank=True, choices=[
        (1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent')
    ], help_text="User rating for the response")
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['agent_used']),
            models.Index(fields=['-timestamp']),
            models.Index(fields=['is_guardrails_blocked']),
        ]
    
    def __str__(self):
        return f"Message in {self.session.session_id} - {self.agent_used}"
    
    def save(self, *args, **kwargs):
        # Auto-detect if message was blocked by guardrails
        if self.agent_used == 'guardrails_blocked':
            self.is_guardrails_blocked = True
        
        # Auto-detect if response contains code (simple heuristic)
        if any(keyword in self.bot_response.lower() for keyword in 
               ['def ', 'function', 'class ', 'import ', '```', 'code:', '<code>']):
            self.has_code = True
        
        # Update session's last agent used
        if not self.is_guardrails_blocked:
            self.session.last_agent_used = self.agent_used
            self.session.save(update_fields=['last_agent_used', 'updated_at'])
        
        super().save(*args, **kwargs)

class ConversationSummary(models.Model):
    """Store AI-generated conversation summaries"""
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE)
    summary = models.TextField()
    key_topics = models.JSONField(default=list, help_text="List of main topics discussed")
    technologies_mentioned = models.JSONField(default=list, help_text="Technologies/languages mentioned")
    generated_at = models.DateTimeField(auto_now=True)
    token_count = models.IntegerField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Conversation summaries"
    
    def __str__(self):
        return f"Summary for {self.session.session_id}"

class UserPreference(models.Model):
    """Store user preferences for the chatbot"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Memory preferences
    default_memory_enabled = models.BooleanField(default=True)
    max_memory_messages = models.IntegerField(default=10, help_text="Max messages to remember")
    
    # Agent preferences
    preferred_agent = models.CharField(max_length=50, blank=True, choices=[
        ('python_agent', 'Python Expert'),
        ('web_agent', 'Web Development Expert'),
        ('database_agent', 'Database Expert'),
        ('algorithm_agent', 'Algorithm Expert'),
        ('debug_agent', 'Debug Expert'),
        ('architecture_agent', 'Architecture Expert'),
    ])
    
    # Response preferences
    prefer_detailed_responses = models.BooleanField(default=True)
    include_examples = models.BooleanField(default=True)
    include_explanations = models.BooleanField(default=True)
    
    # Guardrails preferences
    strict_guardrails = models.BooleanField(default=True, help_text="Strict coding-only mode")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"

class AgentUsageStats(models.Model):
    """Track agent usage statistics"""
    agent_name = models.CharField(max_length=50)
    date = models.DateField(default=timezone.now)
    usage_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    avg_response_time_ms = models.FloatField(null=True, blank=True)
    
    class Meta:
        unique_together = ('agent_name', 'date')
        indexes = [
            models.Index(fields=['agent_name', 'date']),
            models.Index(fields=['-date']),
        ]
    
    def __str__(self):
        return f"{self.agent_name} stats for {self.date}"
    
    @property
    def success_rate(self):
        if self.usage_count == 0:
            return 0
        return round((self.success_count / self.usage_count) * 100, 2)

class GuardrailsLog(models.Model):
    """Log blocked queries for analysis"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    blocked_query = models.TextField()
    classification_reason = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Analysis fields
    query_category = models.CharField(max_length=50, blank=True, choices=[
        ('general_chat', 'General Conversation'),
        ('personal', 'Personal Questions'),
        ('news', 'News/Current Events'),
        ('math_unrelated', 'Math (Non-Programming)'),
        ('other', 'Other'),
    ])
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['query_category']),
        ]
    
    def __str__(self):
        return f"Blocked query: {self.blocked_query[:50]}..."

