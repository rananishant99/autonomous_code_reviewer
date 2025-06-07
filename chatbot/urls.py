from django.urls import path
from .views import (
    CodeChatView, 
    ChatHistoryView, 
    ChatSessionListView,
    DeleteChatSessionView,

    ConversationSummaryView,
    ClearMemoryView,
    GuardrailsTestView,
  
)

app_name = 'chatbot'

urlpatterns = [
    # Main chat endpoint with memory support
    path('chat/', CodeChatView.as_view(), name='code_chat'),
    
    # Chat history and memory management
    path('history/<str:session_id>/', ChatHistoryView.as_view(), name='chat_history'),
    path('summary/<str:session_id>/', ConversationSummaryView.as_view(), name='conversation_summary'),
    path('memory/<str:session_id>/clear/', ClearMemoryView.as_view(), name='clear_memory'),
    
    # Session management
    path('sessions/', ChatSessionListView.as_view(), name='chat_sessions_list'),
    path('sessions/<str:session_id>/delete/', DeleteChatSessionView.as_view(), name='delete_session'),
    
    # Guardrails testing
    path('guardrails/test/', GuardrailsTestView.as_view(), name='test_guardrails'),


]