"""
URL configuration for autonomous_code_reviewer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    """API root endpoint with available endpoints"""
    return JsonResponse({
        'message': 'Code Suggestion Chatbot API',
        'version': '1.0',
        'endpoints': {
            'chat': '/api/chatbot/chat/',
            'history': '/api/chatbot/history/<session_id>/',
            'sessions': '/api/chatbot/sessions/',
            'agents': '/api/chatbot/agents/',
            'stats': '/api/chatbot/stats/',
            'admin': '/admin/',
        },
        'documentation': 'Send POST requests to /api/chatbot/chat/ with {"message": "your code question"}'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('agent/', include('review.urls')),
    path('bot/', include('chatbot.urls')),
]
