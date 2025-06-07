# chatbot/agents.py
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
import yaml
from pathlib import Path
import re
import json
from typing import Dict, Any, List
from django.core.cache import cache
from django.conf import settings


class PromptLoader:
    """Utility class to load prompts from YAML file"""
    
    def __init__(self, prompts_file_path: str = None):
        if prompts_file_path is None:
            # Look for prompts.yml in the same directory as this file
            current_dir = Path(__file__).parent
            self.prompts_file_path = current_dir / "prompts.yml"
            print(f"Looking for prompts file at: {self.prompts_file_path}")
        else:
            self.prompts_file_path = Path(prompts_file_path)
        
        self._prompts = None
    
    def load_prompts(self) -> dict:
        """Load prompts from YAML file with fallback to hardcoded prompts"""
        if self._prompts is None:
            try:
                if self.prompts_file_path.exists():
                    with open(self.prompts_file_path, 'r', encoding='utf-8') as file:
                        self._prompts = yaml.safe_load(file)
                        print(f"Successfully loaded prompts from {self.prompts_file_path}")
                else:
                    print(f"Prompts file not found at {self.prompts_file_path}, using fallback prompts")
                    self._prompts = self._get_fallback_prompts()
            except Exception as e:
                print(f"Error loading prompts: {e}, using fallback prompts")
                self._prompts = self._get_fallback_prompts()
        return self._prompts
    
    def _get_fallback_prompts(self) -> dict:
        """Fallback prompts if YAML file is not available"""
        return {
            'guardrails': {
                'classification_prompt': """
You are a query classifier for a code assistance chatbot. Your job is to determine if a user query is related to programming, software development, or coding.

CODING-RELATED queries include:
- Programming languages (Python, JavaScript, Java, C++, etc.)
- Web development (HTML, CSS, React, Django, etc.)
- Database queries and design
- Algorithms and data structures
- Debugging and troubleshooting code
- Software architecture and design patterns
- Code optimization and best practices
- Framework-specific questions
- API development
- Testing and deployment
- Development tools and IDEs

NON-CODING queries include:
- General conversation
- Personal questions
- News and current events
- Math problems unrelated to programming
- General knowledge questions
- Weather, sports, entertainment
- Medical or legal advice
- Creative writing unrelated to code

Query: "{query}"

Respond with ONLY "CODING" or "NON_CODING" based on whether this query is related to programming/software development.
                """,
                'blocked_response': """I'm a specialized coding assistant designed to help with programming and software development questions only. 

I can help you with:
- Programming languages (Python, JavaScript, Java, etc.)
- Web development (HTML, CSS, React, Django, etc.)
- Database design and queries
- Algorithms and data structures
- Debugging and code optimization
- Software architecture and design patterns
- API development and testing

Please ask me a coding-related question, and I'll be happy to help!"""
            },
            'agents': {
                'python_agent': {
                    'base_prompt': """
You are a Python coding expert with memory of our previous conversations. Provide clean, efficient Python code solutions.
Always include:
1. Complete, runnable code
2. Clear comments explaining the logic
3. Best practices and conventions
4. Error handling where appropriate
5. Consider any previous context from our conversation

User Query: {query}

Provide a comprehensive Python solution:
                    """
                },
                'web_agent': {
                    'base_prompt': """
You are a web development expert with memory of our previous conversations, specializing in HTML, CSS, JavaScript, React, Django, Flask, etc.
Always provide:
1. Complete, working code examples
2. Modern best practices
3. Responsive design considerations
4. Security considerations where relevant
5. Build upon any previous discussion we've had

User Query: {query}

Provide a comprehensive web development solution:
                    """
                },
                'database_agent': {
                    'base_prompt': """
You are a database expert with memory of our previous conversations, specializing in SQL, NoSQL, ORM, and database design.
Always provide:
1. Optimized queries
2. Proper indexing suggestions
3. Schema design best practices
4. Performance considerations
5. Reference any database discussions we've had before

User Query: {query}

Provide a comprehensive database solution:
                    """
                },
                'algorithm_agent': {
                    'base_prompt': """
You are an algorithms and data structures expert with memory of our previous conversations.
Always provide:
1. Optimal algorithm implementation
2. Time and space complexity analysis
3. Alternative approaches
4. Step-by-step explanation
5. Build on any algorithmic concepts we've discussed

User Query: {query}

Provide a comprehensive algorithmic solution:
                    """
                },
                'debug_agent': {
                    'base_prompt': """
You are a debugging expert with memory of our previous conversations. Help identify and fix code issues.
Always provide:
1. Clear explanation of the problem
2. Step-by-step debugging approach
3. Fixed code with explanations
4. Prevention strategies
5. Consider any debugging patterns we've discussed before

User Query: {query}

Provide comprehensive debugging assistance:
                    """
                },
                'architecture_agent': {
                    'base_prompt': """
You are a software architecture expert with memory of our previous conversations.
Always provide:
1. System design recommendations
2. Design patterns suggestions
3. Scalability considerations
4. Technology stack recommendations
5. Build upon any architectural discussions we've had

User Query: {query}

Provide comprehensive architectural guidance:
                    """
                }
            },
            'memory': {
                'enhanced_template_suffix': """

Previous conversation context (if any):
{chat_history}

Based on the context above, provide a response that builds upon our previous discussion where relevant.
                """
            }
        }
    
    def get_prompt(self, category: str, prompt_name: str) -> str:
        """Get a specific prompt by category and name"""
        prompts = self.load_prompts()
        try:
            if category in prompts and prompt_name in prompts[category]:
                return prompts[category][prompt_name]
            else:
                print(f"Prompt not found: {category}.{prompt_name}")
                return ""
        except Exception as e:
            print(f"Error getting prompt {category}.{prompt_name}: {e}")
            return ""


class PersistentMemory:
    """Simple memory class that loads conversation history from database"""
    
    def __init__(self, session_id: str, max_messages: int = 10):
        self.session_id = session_id
        self.max_messages = max_messages
    
    def get_conversation_history(self) -> str:
        """Get formatted conversation history"""
        try:
            from .models import ChatMessage, ChatSession
            
            # Get session
            session = ChatSession.objects.get(session_id=self.session_id)
            
            # Get recent messages (excluding guardrails blocked)
            recent_messages = session.messages.exclude(
                agent_used='guardrails_blocked'
            ).order_by('-timestamp')[:self.max_messages]
            
            # Format conversation history
            history = []
            for msg in reversed(recent_messages):
                history.extend([
                    f"Human: {msg.user_message}",
                    f"Assistant: {msg.bot_response[:300]}..."  # Truncate long responses
                ])
            
            return "\n".join(history) if history else ""
            
        except Exception as e:
            print(f"Memory loading error: {e}")
            return ""
    
    def clear(self) -> None:
        """Clear memory cache if any"""
        cache.delete(f"memory_{self.session_id}")


class GuardrailsLLM:
    """LLM for checking if queries are code-related"""
    
    def __init__(self, openai_api_key, prompt_loader: PromptLoader = None):
        self.llm = ChatOpenAI(
            temperature=0.0,
            model=os.getenv('GUARDRAILS_MODEL', 'gpt-4o-mini'),
            openai_api_key=openai_api_key
        )
        
        self.prompt_loader = prompt_loader or PromptLoader()
        
        # Load classification prompt from YAML
        classification_template = self.prompt_loader.get_prompt('guardrails', 'classification_prompt')
        if classification_template:
            self.classification_prompt = PromptTemplate(
                input_variables=["query"],
                template=classification_template
            )
        else:
            # Fallback prompt if loading fails
            self.classification_prompt = PromptTemplate(
                input_variables=["query"],
                template="Classify if this is coding-related: {query}. Respond CODING or NON_CODING."
            )
        
        # Load blocked response from YAML
        self.blocked_response = self.prompt_loader.get_prompt('guardrails', 'blocked_response')
        if not self.blocked_response:
            self.blocked_response = "I can only help with coding-related questions. Please ask a programming question."
    
    def is_coding_related(self, query: str) -> bool:
        """Check if query is coding-related"""
        try:
            response = self.llm.invoke([
                HumanMessage(content=self.classification_prompt.format(query=query))
            ])
            
            classification = response.content.strip().upper()
            return classification == "CODING"
            
        except Exception as e:
            # If classification fails, be permissive and allow the query
            print(f"Guardrails classification error: {e}")
            return True
    
    def get_blocked_response(self) -> str:
        """Get the response for blocked queries"""
        return self.blocked_response


class CodeSuggestionAgents:
    def __init__(self, openai_api_key, session_id=None, prompts_file_path=None):
        self.openai_api_key = openai_api_key
        self.session_id = session_id
        self.llm = ChatOpenAI(
            temperature=0.1,
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            openai_api_key=openai_api_key
        )
        
        # Initialize prompt loader
        self.prompt_loader = PromptLoader(prompts_file_path)
        
        # Initialize guardrails with prompt loader
        self.guardrails = GuardrailsLLM(openai_api_key, self.prompt_loader)
        
        # Initialize memory if session_id provided
        self.memory = PersistentMemory(session_id) if session_id else None
        
        self.agents = self._create_agents()
    
    def _create_memory_aware_chain(self, prompt_template: PromptTemplate) -> LLMChain:
        """Create LLMChain with memory support"""
        if self.memory:
            # Load memory enhancement template from YAML
            memory_suffix = self.prompt_loader.get_prompt('memory', 'enhanced_template_suffix')
            
            if memory_suffix:
                # Create enhanced prompt that includes conversation history
                enhanced_template = prompt_template.template + memory_suffix
                
                memory_prompt = PromptTemplate(
                    input_variables=["query", "chat_history"],
                    template=enhanced_template
                )
                return LLMChain(llm=self.llm, prompt=memory_prompt)
            else:
                return LLMChain(llm=self.llm, prompt=prompt_template)
        else:
            return LLMChain(llm=self.llm, prompt=prompt_template)
    
    def _create_agents(self):
        """Create all agents using prompts from YAML"""
        return {
            'python_agent': self._create_python_agent(),
            'web_agent': self._create_web_agent(),
            'database_agent': self._create_database_agent(),
            'algorithm_agent': self._create_algorithm_agent(),
            'debug_agent': self._create_debug_agent(),
            'architecture_agent': self._create_architecture_agent()
        }
    
    def _create_python_agent(self):
        """Create Python agent with YAML prompt"""
        agent_config = self.prompt_loader.get_prompt('agents', 'python_agent')
        if agent_config and isinstance(agent_config, dict) and 'base_prompt' in agent_config:
            python_template = agent_config['base_prompt']
        else:
            python_template = "You are a Python expert. Help with: {query}"
        
        python_prompt = PromptTemplate(
            input_variables=["query"],
            template=python_template
        )
        return self._create_memory_aware_chain(python_prompt)
    
    def _create_web_agent(self):
        """Create Web agent with YAML prompt"""
        agent_config = self.prompt_loader.get_prompt('agents', 'web_agent')
        if agent_config and isinstance(agent_config, dict) and 'base_prompt' in agent_config:
            web_template = agent_config['base_prompt']
        else:
            web_template = "You are a web development expert. Help with: {query}"
        
        web_prompt = PromptTemplate(
            input_variables=["query"],
            template=web_template
        )
        return self._create_memory_aware_chain(web_prompt)
    
    def _create_database_agent(self):
        """Create Database agent with YAML prompt"""
        agent_config = self.prompt_loader.get_prompt('agents', 'database_agent')
        if agent_config and isinstance(agent_config, dict) and 'base_prompt' in agent_config:
            db_template = agent_config['base_prompt']
        else:
            db_template = "You are a database expert. Help with: {query}"
        
        db_prompt = PromptTemplate(
            input_variables=["query"],
            template=db_template
        )
        return self._create_memory_aware_chain(db_prompt)
    
    def _create_algorithm_agent(self):
        """Create Algorithm agent with YAML prompt"""
        agent_config = self.prompt_loader.get_prompt('agents', 'algorithm_agent')
        if agent_config and isinstance(agent_config, dict) and 'base_prompt' in agent_config:
            algo_template = agent_config['base_prompt']
        else:
            algo_template = "You are an algorithms expert. Help with: {query}"
        
        algo_prompt = PromptTemplate(
            input_variables=["query"],
            template=algo_template
        )
        return self._create_memory_aware_chain(algo_prompt)
    
    def _create_debug_agent(self):
        """Create Debug agent with YAML prompt"""
        agent_config = self.prompt_loader.get_prompt('agents', 'debug_agent')
        if agent_config and isinstance(agent_config, dict) and 'base_prompt' in agent_config:
            debug_template = agent_config['base_prompt']
        else:
            debug_template = "You are a debugging expert. Help with: {query}"
        
        debug_prompt = PromptTemplate(
            input_variables=["query"],
            template=debug_template
        )
        return self._create_memory_aware_chain(debug_prompt)
    
    def _create_architecture_agent(self):
        """Create Architecture agent with YAML prompt"""
        agent_config = self.prompt_loader.get_prompt('agents', 'architecture_agent')
        if agent_config and isinstance(agent_config, dict) and 'base_prompt' in agent_config:
            arch_template = agent_config['base_prompt']
        else:
            arch_template = "You are a software architecture expert. Help with: {query}"
        
        arch_prompt = PromptTemplate(
            input_variables=["query"],
            template=arch_template
        )
        return self._create_memory_aware_chain(arch_prompt)
    
    def classify_query(self, query):
        """Classify the user query to determine which agent to use"""
        query_lower = query.lower()
        
        # Enhanced keywords for different agents
        python_keywords = ['python', 'django', 'flask', 'pandas', 'numpy', 'matplotlib', 'fastapi', 'pytest', 'pip']
        web_keywords = ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'frontend', 'web', 'node', 'express', 'bootstrap']
        db_keywords = ['sql', 'database', 'mysql', 'postgresql', 'mongodb', 'query', 'schema', 'orm', 'redis', 'elasticsearch']
        algo_keywords = ['algorithm', 'sorting', 'searching', 'data structure', 'complexity', 'optimize', 'leetcode', 'binary tree', 'graph']
        debug_keywords = ['debug', 'error', 'fix', 'bug', 'issue', 'problem', 'not working', 'exception', 'traceback']
        arch_keywords = ['architecture', 'design pattern', 'system design', 'scalability', 'microservices', 'api design', 'deployment']
        
        # Priority-based classification
        if any(keyword in query_lower for keyword in debug_keywords):
            return 'debug_agent'
        elif any(keyword in query_lower for keyword in arch_keywords):
            return 'architecture_agent'
        elif any(keyword in query_lower for keyword in algo_keywords):
            return 'algorithm_agent'
        elif any(keyword in query_lower for keyword in db_keywords):
            return 'database_agent'
        elif any(keyword in query_lower for keyword in web_keywords):
            return 'web_agent'
        elif any(keyword in query_lower for keyword in python_keywords):
            return 'python_agent'
        else:
            return 'python_agent'  # Default to Python agent
    
    def get_code_suggestion(self, query):
        """Main method to get code suggestions with guardrails and memory"""
        
        # Step 1: Check if query is coding-related using guardrails
        if not self.guardrails.is_coding_related(query):
            return {
                'response': self.guardrails.get_blocked_response(),
                'agent_used': 'guardrails_blocked',
                'success': True,
                'guardrails_blocked': True
            }
        
        # Step 2: Classify and route to appropriate agent
        agent_type = self.classify_query(query)
        agent = self.agents[agent_type]
        
        try:
            # Step 3: Get response from specialized agent
            if self.memory:
                # Get conversation history
                chat_history = self.memory.get_conversation_history()
                response = agent.run(query=query, chat_history=chat_history)
            else:
                response = agent.run(query=query)
            
            return {
                'response': response,
                'agent_used': agent_type,
                'success': True,
                'guardrails_blocked': False
            }
        except Exception as e:
            print(f"Error in get_code_suggestion: {e}")
            return {
                'response': f"Sorry, I encountered an error while processing your coding question: {str(e)}",
                'agent_used': agent_type,
                'success': False,
                'guardrails_blocked': False
            }
    
    def reload_prompts(self):
        """Reload prompts from YAML file and recreate agents"""
        # Clear cached prompts
        self.prompt_loader._prompts = None
        
        # Recreate guardrails with new prompts
        self.guardrails = GuardrailsLLM(self.openai_api_key, self.prompt_loader)
        
        # Recreate agents with new prompts
        self.agents = self._create_agents()
        
        return "Prompts reloaded successfully"
    
    def get_conversation_summary(self):
        """Get a summary of the current conversation"""
        if not self.memory:
            return "No conversation history available."
        
        try:
            from .models import ChatMessage, ChatSession
            
            session = ChatSession.objects.get(session_id=self.session_id)
            messages = session.messages.all()
            
            if not messages.exists():
                return "No conversation history yet."
            
            # Create summary
            total_messages = messages.count()
            agents_used = list(messages.values_list('agent_used', flat=True).distinct())
            
            summary = f"""Conversation Summary:
- Total messages: {total_messages}
- Agents used: {', '.join(agents_used)}
- Session started: {session.created_at.strftime('%Y-%m-%d %H:%M')}
- Last activity: {session.updated_at.strftime('%Y-%m-%d %H:%M')}
"""
            return summary
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def clear_memory(self):
        """Clear conversation memory"""
        if self.memory:
            self.memory.clear()
            return "Conversation memory cleared."
        return "No memory to clear."