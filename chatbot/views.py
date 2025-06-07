# chatbot/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.db.models import Count
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid
import json

from .models import ChatSession, ChatMessage
from .agents import CodeSuggestionAgents

class CodeChatView(APIView):
    """Enhanced chat view with memory management and guardrails"""
    
    def post(self, request):
        try:
            user_message = request.data.get('message', '')
            session_id = request.data.get('session_id', str(uuid.uuid4()))
            use_memory = request.data.get('use_memory', True)  # Enable memory by default
            
            if not user_message:
                return Response({
                    'error': 'Message is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get or create chat session
            session, created = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={'user': request.user if request.user.is_authenticated else None}
            )
            
            # Initialize agents with memory if enabled
            if use_memory:
                agents = CodeSuggestionAgents(
                    openai_api_key=getattr(settings, 'OPENAI_API_KEY', ''),
                    session_id=session_id
                )
            else:
                agents = CodeSuggestionAgents(
                    openai_api_key=getattr(settings, 'OPENAI_API_KEY', '')
                )
            
            # Get code suggestion from agents (with guardrails)
            result = agents.get_code_suggestion(user_message)
            
            # Save chat message only if not blocked by guardrails
            if not result.get('guardrails_blocked', False):
                ChatMessage.objects.create(
                    session=session,
                    user_message=user_message,
                    bot_response=result['response'],
                    agent_used=result['agent_used']
                )
            else:
                # For blocked queries, save with special agent type
                ChatMessage.objects.create(
                    session=session,
                    user_message=user_message,
                    bot_response=result['response'],
                    agent_used='guardrails_blocked'
                )
            
            return Response({
                'response': result['response'],
                'agent_used': result['agent_used'],
                'session_id': session_id,
                'success': result['success'],
                'guardrails_blocked': result.get('guardrails_blocked', False),
                'memory_enabled': use_memory
            })
            
        except Exception as e:
            return Response({
                'error': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatHistoryView(APIView):
    """Enhanced chat history with memory context"""
    
    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = session.messages.all().order_by('timestamp')
            
            history = []
            coding_messages = 0
            blocked_messages = 0
            
            for msg in messages:
                history.append({
                    'user_message': msg.user_message,
                    'bot_response': msg.bot_response,
                    'agent_used': msg.agent_used,
                    'timestamp': msg.timestamp.isoformat(),
                    'blocked_by_guardrails': msg.agent_used == 'guardrails_blocked'
                })
                
                if msg.agent_used == 'guardrails_blocked':
                    blocked_messages += 1
                else:
                    coding_messages += 1
            
            return Response({
                'session_id': session_id,
                'history': history,
                'statistics': {
                    'total_messages': len(history),
                    'coding_messages': coding_messages,
                    'blocked_messages': blocked_messages,
                    'session_duration': str(session.updated_at - session.created_at)
                }
            })
            
        except ChatSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Error fetching history: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ConversationSummaryView(APIView):
    """Get conversation summary for a session"""
    
    def get(self, request, session_id):
        try:
            agents = CodeSuggestionAgents(
                openai_api_key=getattr(settings, 'OPENAI_API_KEY', ''),
                session_id=session_id
            )
            
            summary = agents.get_conversation_summary()
            
            return Response({
                'session_id': session_id,
                'summary': summary
            })
            
        except Exception as e:
            return Response({
                'error': f'Error generating summary: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ClearMemoryView(APIView):
    """Clear conversation memory for a session"""
    
    def post(self, request, session_id):
        try:
            agents = CodeSuggestionAgents(
                openai_api_key=getattr(settings, 'OPENAI_API_KEY', ''),
                session_id=session_id
            )
            
            result = agents.clear_memory()
            
            return Response({
                'session_id': session_id,
                'message': result
            })
            
        except Exception as e:
            return Response({
                'error': f'Error clearing memory: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GuardrailsTestView(APIView):
    """Test if a query would be blocked by guardrails"""
    
    def post(self, request):
        try:
            query = request.data.get('query', '')
            
            if not query:
                return Response({
                    'error': 'Query is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            agents = CodeSuggestionAgents(
                openai_api_key=getattr(settings, 'OPENAI_API_KEY', '')
            )
            
            is_coding_related = agents.guardrails.is_coding_related(query)
            agent_type = agents.classify_query(query)
            
            return Response({
                'query': query,
                'is_coding_related': is_coding_related,
                'would_be_blocked': not is_coding_related,
                'suggested_agent': agent_type if is_coding_related else None
            })
            
        except Exception as e:
            return Response({
                'error': f'Error testing guardrails: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatSessionListView(APIView):
    """Enhanced session list with memory and guardrails stats"""
    
    def get(self, request):
        try:
            sessions = ChatSession.objects.all().order_by('-updated_at')
            
            # Filter by user if authenticated
            if request.user.is_authenticated:
                sessions = sessions.filter(user=request.user)
            
            session_data = []
            for session in sessions:
                messages = session.messages.all()
                message_count = messages.count()
                last_message = messages.last()
                
                # Calculate stats
                blocked_count = messages.filter(agent_used='guardrails_blocked').count()
                coding_count = message_count - blocked_count
                
                session_data.append({
                    'session_id': session.session_id,
                    'created_at': session.created_at.isoformat(),
                    'updated_at': session.updated_at.isoformat(),
                    'message_count': message_count,
                    'coding_messages': coding_count,
                    'blocked_messages': blocked_count,
                    'last_message': last_message.user_message[:100] + '...' if last_message and len(last_message.user_message) > 100 else last_message.user_message if last_message else None,
                    'user': session.user.username if session.user else 'Anonymous',
                    'has_memory': message_count > 1  # Sessions with multiple messages have memory context
                })
            
            return Response({
                'sessions': session_data,
                'total_sessions': len(session_data)
            })
            
        except Exception as e:
            return Response({
                'error': f'Error fetching sessions: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteChatSessionView(APIView):
    """Delete a specific chat session and its memory"""
    
    def delete(self, request, session_id):
        try:
            session = ChatSession.objects.get(session_id=session_id)
            
            # Check if user owns the session (if authenticated)
            if request.user.is_authenticated and session.user and session.user != request.user:
                return Response({
                    'error': 'You can only delete your own sessions'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Clear memory before deleting
            try:
                agents = CodeSuggestionAgents(
                    openai_api_key=getattr(settings, 'OPENAI_API_KEY', ''),
                    session_id=session_id
                )
                agents.clear_memory()
            except:
                pass  # Continue even if memory clearing fails
            
            session.delete()
            
            return Response({
                'message': f'Session {session_id} and its memory deleted successfully'
            })
            
        except ChatSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Error deleting session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





