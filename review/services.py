import os
import yaml
import requests
import json
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from datetime import datetime
from pathlib import Path
from .models import Repository, PullRequest, ReviewRequest, ReviewResult
from authentication.utils import decrypt_token
class ConfigService:
    """Centralized configuration management from environment variables"""
    
    @staticmethod
    def get_github_config() -> Dict[str, str]:
        """Get GitHub-related configuration"""
        return {
            # 'token': os.getenv('GITHUB_TOKEN'),
            'base_url': os.getenv('GITHUB_API_BASE_URL', 'https://api.github.com'),
            'timeout': int(os.getenv('API_TIMEOUT', '30')),
            'max_retries': int(os.getenv('API_MAX_RETRIES', '3')),
            'rate_limit': int(os.getenv('API_RATE_LIMIT_PER_HOUR', '1000'))
        }
    
    @staticmethod
    def get_openai_config() -> Dict:
        """Get OpenAI-related configuration"""
        return {
            'api_key': os.getenv('OPENAI_API_KEY'),
            'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            'temperature': float(os.getenv('OPENAI_TEMPERATURE', '0')),
            'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
        }
    
    @staticmethod
    def get_prompts_config() -> Dict[str, str]:
        """Get prompts-related configuration"""
        return {
            'file_path': os.getenv('PROMPTS_FILE_PATH', 'api/prompts.yml'),
            'auto_reload': os.getenv('AUTO_RELOAD_PROMPTS', 'True').lower() == 'true'
        }
    
    @staticmethod
    def get_logging_config() -> Dict:
        """Get logging configuration"""
        return {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'debug_enabled': os.getenv('ENABLE_DEBUG_LOGGING', 'False').lower() == 'true'
        }
    
    @staticmethod
    def validate_config() -> Dict[str, bool]:
        """Validate that all required environment variables are set"""
        github_config = ConfigService.get_github_config()
        openai_config = ConfigService.get_openai_config()
        
        validation = {
            'github_token': bool(github_config['token']),
            'github_base_url': bool(github_config['base_url']),
            'openai_api_key': bool(openai_config['api_key']),
            'all_valid': False
        }
        
        validation['all_valid'] = all([
            validation['github_token'],
            validation['github_base_url'],
            validation['openai_api_key']
        ])
        
        return validation

class PromptManager:
    def __init__(self, prompts_file_path: str = None):
        if prompts_file_path is None:
            # Get prompts file path from environment
            prompts_config = ConfigService.get_prompts_config()
            prompts_file_path = prompts_config['file_path']
        
        self.prompts_file_path = Path(prompts_file_path)
        self.auto_reload = ConfigService.get_prompts_config()['auto_reload']
        self.prompts = self.load_prompts()
    
    def load_prompts(self) -> Dict:
        """Load prompts from YAML file"""
        try:
            with open(self.prompts_file_path, 'r', encoding='utf-8') as file:
                prompts = yaml.safe_load(file)
                if ConfigService.get_logging_config()['debug_enabled']:
                    print(f"✅ Loaded prompts from {self.prompts_file_path}")
                return prompts
        except FileNotFoundError:
            print(f"⚠️  Prompts file not found: {self.prompts_file_path}")
            return self.get_default_prompts()
        except yaml.YAMLError as e:
            print(f"❌ Error parsing YAML file: {e}")
            return self.get_default_prompts()
    
    def get_default_prompts(self) -> Dict:
        """Fallback prompts if YAML file is not available"""
        return {
            'file_analysis': {
                'system_prompt': """You are a senior software architect and code reviewer. Provide comprehensive analysis focusing on:

    **CODE QUALITY ASSESSMENT:**
    1. **Design Patterns & Architecture**: Identify anti-patterns, suggest better architectural approaches
    2. **Performance Analysis**: Identify bottlenecks, memory issues, algorithmic complexity problems
    3. **Security Review**: Find vulnerabilities, injection risks, authentication issues
    4. **Maintainability**: Code readability, modularity, documentation needs
    5. **Best Practices**: Language-specific conventions, error handling, testing gaps

    **DETAILED FEEDBACK FORMAT:**
    For each issue found:
    - **Severity**: CRITICAL/HIGH/MEDIUM/LOW
    - **Category**: Performance/Security/Maintainability/Style/Logic
    - **Location**: Exact line numbers from the diff
    - **Problem**: Clear description of the issue
    - **Impact**: Why this matters (performance, security, maintenance)
    - **Solution**: Specific code improvement with examples

    Be specific, actionable, and focus on making the code production-ready.""",
                
                'user_prompt': """
    **File**: {filename}
    **Language**: {language}
    **Changes**: +{additions} -{deletions} lines

    **Old Code**:
    {old_code}

    **New Code**:
    {new_code}

    **Diff Analysis**:
    {diff}

    **Code Changes Summary**:
    {changes_summary}

    Please provide detailed analysis with specific code improvements.
    """
            },
            'code_improvements': {
                'system_prompt': """You are an expert code reviewer. Analyze the provided code changes and give specific improvements.

    TASK: Provide code improvements in this EXACT format:

    ## 🎯 ORIGINAL CODE vs IMPROVED CODE

    ### Issue 1: [Problem Description]
    **Severity**: HIGH/MEDIUM/LOW
    **Category**: Performance/Security/Quality/Style

    **Original Code:**
    ```[language]
    [show the actual problematic code]
    ```

    **Improved Code:**
    ```[language]
    [show the improved version]
    ```

    **Why This Is Better:**
    - [Specific technical reason 1]
    - [Specific technical reason 2]
    - [Measurable benefit]

    REQUIREMENTS:
    - Always find at least 1-2 improvement opportunities
    - Be specific about what to change and why
    - Provide working code examples
    - Focus on practical, implementable suggestions""",
                
                'user_prompt': """Please analyze this code change:

    File: {file_path}
    Language: {language}

    Added Lines:
    {added_lines}

    Removed Lines:
    {removed_lines}

    Context:
    {context}

    Provide specific improvements with before/after examples."""
            }
        }
    
    def get_prompt(self, prompt_type: str, prompt_part: str = 'system_prompt') -> str:
        """Get a specific prompt by type and part"""
        try:
            return self.prompts[prompt_type][prompt_part]
        except KeyError:
            if ConfigService.get_logging_config()['debug_enabled']:
                print(f"⚠️  Prompt not found: {prompt_type}.{prompt_part}")
            return self.get_default_prompts().get(prompt_type, {}).get(prompt_part, "Default prompt not available")
    
    def get_prompt_template(self, prompt_type: str) -> ChatPromptTemplate:
        """Get a ChatPromptTemplate for a specific prompt type"""
        system_prompt = self.get_prompt(prompt_type, 'system_prompt')
        user_prompt = self.get_prompt(prompt_type, 'user_prompt')
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])
    
    def reload_prompts(self):
        """Reload prompts from file (useful for development)"""
        self.prompts = self.load_prompts()
        if ConfigService.get_logging_config()['debug_enabled']:
            print("🔄 Prompts reloaded from file")

class GitHubService:
    def __init__(self, user):
        # Load configuration from environment variables
        self.config = ConfigService.get_github_config()
        
        self.token = decrypt_token(user.github_tokens.latest('created_at').token)
        self.base_url = self.config['base_url']
        self.timeout = self.config['timeout']
        self.max_retries = self.config['max_retries']
        
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        if not self.base_url:
            raise ValueError("GITHUB_API_BASE_URL environment variable is required")
        
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Debug logging
        if ConfigService.get_logging_config()['debug_enabled']:
            print(f"🔧 GitHub API configured: {self.base_url}")
            print(f"⏱️  Timeout: {self.timeout}s, Max retries: {self.max_retries}")
    
    def _make_request(self, url: str, headers: Dict = None, params: Dict = None, method: str = 'GET'):
        """Make HTTP request with retry logic and timeout"""
        if headers is None:
            headers = self.headers
        
        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                else:
                    response = requests.request(method, url, headers=headers, params=params, timeout=self.timeout)
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    if ConfigService.get_logging_config()['debug_enabled']:
                        print(f"⚠️  Request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                    continue
                else:
                    raise e
    
    def get_user_repositories(self, page=1, per_page=30):
        """Get user's repositories"""
        url = f"{self.base_url}/user/repos"
        params = {
            "page": page,
            "per_page": per_page,
            "sort": "updated",
            "type": "all"
        }
        response = self._make_request(url, params=params)
        return response.json()
    
    def get_repository_prs(self, owner: str, repo: str, state="open", page=1, per_page=20):
        """Get PRs for a specific repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        params = {
            "state": state,
            "page": page,
            "per_page": per_page,
            "sort": "updated",
            "direction": "desc"
        }
        response = self._make_request(url, params=params)
        return response.json()
    
    def get_pr_details(self, owner: str, repo: str, pr_number: int):
        """Get PR details from GitHub"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        response = self._make_request(url)
        return response.json()
    
    def get_pr_diff(self, owner: str, repo: str, pr_number: int):
        """Get PR diff from GitHub"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        response = self._make_request(url, headers=headers)
        return response.text
    
    def get_pr_files(self, owner: str, repo: str, pr_number: int):
        """Get changed files in PR"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = self._make_request(url)
        return response.json()
    
    def get_api_info(self) -> Dict:
        """Get GitHub API information and rate limits"""
        try:
            url = f"{self.base_url}/rate_limit"
            response = self._make_request(url)
            rate_limit_info = response.json()
            
            return {
                'base_url': self.base_url,
                'rate_limit': rate_limit_info.get('rate', {}),
                'timeout': self.timeout,
                'max_retries': self.max_retries,
                'status': 'connected'
            }
        except Exception as e:
            return {
                'base_url': self.base_url,
                'status': 'error',
                'error': str(e)
            }

class PRReviewService:
    def __init__(self, prompts_file_path: str = None, user=None):
        # Load OpenAI configuration from environment
        openai_config = ConfigService.get_openai_config()
        self.user = user
        if not openai_config['api_key']:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.llm = ChatOpenAI(
            model=openai_config['model'],
            temperature=openai_config['temperature'],
            max_tokens=openai_config['max_tokens']
        )
        
        self.github_service = GitHubService(self.user)
        self.prompt_manager = PromptManager(prompts_file_path)
        
        # Debug logging
        if ConfigService.get_logging_config()['debug_enabled']:
            print(f"🤖 AI Model configured: {openai_config['model']}")
            print(f"🌡️  Temperature: {openai_config['temperature']}")
            print(f"📏 Max tokens: {openai_config['max_tokens']}")

    def parse_diff_changes_detailed(self, diff: str) -> tuple[str, str, str]:
        """Parse diff to extract old code, new code, and changes summary separately"""
        if not diff:
            return "", "", "No diff available"
        
        lines = diff.split('\n')
        old_code_lines = []
        new_code_lines = []
        changes = []
        line_number = 1
        
        for line in lines:
            if line.startswith('@@'):
                # Extract line number from hunk header
                try:
                    import re
                    match = re.search(r'@@\s*-(\d+)(?:,\d+)?\s*\+(\d+)(?:,\d+)?\s*@@', line)
                    if match:
                        old_line, new_line = match.groups()
                        line_number = int(new_line)
                        changes.append(f"   HUNK: {line}")
                except:
                    pass
            elif line.startswith('-') and not line.startswith('---'):
                # Removed line (old code)
                old_code_lines.append(line[1:])  # Remove the '-' prefix
                changes.append(f"❌ REMOVED (Line ~{line_number}): {line[1:]}")
            elif line.startswith('+') and not line.startswith('+++'):
                # Added line (new code)
                new_code_lines.append(line[1:])  # Remove the '+' prefix
                changes.append(f"✅ ADDED (Line {line_number}): {line[1:]}")
                line_number += 1
            elif line.startswith(' '):
                # Context line (appears in both old and new)
                context_line = line[1:]
                old_code_lines.append(context_line)
                new_code_lines.append(context_line)
                changes.append(f"   CONTEXT (Line {line_number}): {context_line}")
                line_number += 1
        
        # Join the code lines
        old_code = '\n'.join(old_code_lines) if old_code_lines else "No old code found"
        new_code = '\n'.join(new_code_lines) if new_code_lines else "No new code found"
        changes_summary = '\n'.join(changes) if changes else "No meaningful changes found in diff"
        
        return old_code, new_code, changes_summary
    
    def get_service_info(self) -> Dict:
        """Get service configuration information"""
        github_info = self.github_service.get_api_info()
        openai_config = ConfigService.get_openai_config()
        prompts_config = ConfigService.get_prompts_config()
        
        return {
            'github_api': github_info,
            'openai_config': {
                'model': openai_config['model'],
                'temperature': openai_config['temperature'],
                'max_tokens': openai_config['max_tokens']
            },
            'prompts_config': {
                'file_path': str(self.prompt_manager.prompts_file_path),
                'auto_reload': prompts_config['auto_reload'],
                'available_prompts': list(self.prompt_manager.prompts.keys())
            },
            'validation': ConfigService.validate_config()
        }
    
    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        if not file_path:
            return 'Unknown'
            
        file_path = file_path.lower()
        language_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.cs': 'C#',
            '.go': 'Go', '.rs': 'Rust', '.php': 'PHP', '.rb': 'Ruby',
            '.html': 'HTML', '.css': 'CSS', '.sql': 'SQL'
        }
        
        for ext, lang in language_map.items():
            if file_path.endswith(ext):
                return lang
        return 'Unknown'
    
    def parse_diff_changes(self, diff: str) -> str:
        """Parse diff to extract old vs new code changes"""
        if not diff:
            return "No diff content available"
            
        lines = diff.split('\n')
        changes = []
        line_number = 0
        
        for line in lines:
            if line.startswith('@@'):
                import re
                match = re.search(r'@@\s*-(\d+)(?:,\d+)?\s*\+(\d+)(?:,\d+)?\s*@@', line)
                if match:
                    old_line, new_line = match.groups()
                    changes.append(f"\n=== Lines around {new_line} ===")
                    line_number = int(new_line)
            elif line.startswith('-') and not line.startswith('---'):
                changes.append(f"❌ REMOVED (Line ~{line_number}): {line[1:]}")
            elif line.startswith('+') and not line.startswith('+++'):
                changes.append(f"✅ ADDED (Line {line_number}): {line[1:]}")
                line_number += 1
            elif line.startswith(' '):
                changes.append(f"   CONTEXT (Line {line_number}): {line[1:]}")
                line_number += 1
        
        return '\n'.join(changes) if changes else "No meaningful changes found in diff"
    
    def extract_file_diff(self, full_diff: str, filename: str) -> str:
        """Extract diff for a specific file"""
        if not full_diff:
            return f"No diff available for {filename}"
            
        lines = full_diff.split('\n')
        file_diff = []
        in_file = False
        
        for line in lines:
            if line.startswith(f'diff --git a/{filename}') or line.startswith(f'diff --git b/{filename}'):
                in_file = True
            elif line.startswith('diff --git') and in_file:
                break
            elif in_file:
                file_diff.append(line)
        
        return '\n'.join(file_diff) if file_diff else f"No diff content found for {filename}"
    
    async def generate_code_improvements(self, file_path: str, diff: str, language: str) -> str:
        """Generate specific code improvement suggestions using YAML prompts"""
        # Extract actual code changes from diff
        added_lines = []
        removed_lines = []
        context_lines = []
        
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])
            elif line.startswith('-') and not line.startswith('---'):
                removed_lines.append(line[1:])
            elif line.startswith(' '):
                context_lines.append(line[1:])
        
        # Use YAML-based prompt template
        improvement_prompt = self.prompt_manager.get_prompt_template('code_improvements')
        
        try:
            chain = improvement_prompt | self.llm
            improvements = await chain.ainvoke({
                "file_path": file_path,
                "language": language,
                "added_lines": '\n'.join(added_lines[:10]) if added_lines else "No lines added",
                "removed_lines": '\n'.join(removed_lines[:10]) if removed_lines else "No lines removed",
                "context": '\n'.join(context_lines[:5]) if context_lines else "No context available"
            })
            
            return improvements.content
            
        except Exception as e:
            if ConfigService.get_logging_config()['debug_enabled']:
                print(f"❌ Error generating improvements: {e}")
            return self.generate_fallback_improvements(file_path, language, added_lines, removed_lines)
    
    def generate_fallback_improvements(self, file_path: str, language: str, added_lines: List[str], removed_lines: List[str]) -> str:
        """Generate fallback improvements when main generation fails"""
        try:
            # Try to use fallback template from YAML
            fallback_template = self.prompt_manager.get_prompt('fallback_improvement', 'template')
            
            original_code = '\n'.join(removed_lines[:5]) if removed_lines else "# Previous version"
            improved_code = '\n'.join(added_lines[:5]) if added_lines else "# Improved version"
            
            return fallback_template.format(
                language=language,
                original_code=original_code,
                improved_code=improved_code
            )
        except:
            # Ultimate fallback
            improvements = []
            improvements.append("## 🎯 ORIGINAL CODE vs IMPROVED CODE")
            improvements.append("\n### Issue 1: Code Quality Enhancement")
            improvements.append("**Severity**: MEDIUM")
            improvements.append("**Category**: Quality")
            improvements.append("")
            improvements.append("**Original Code:**")
            improvements.append(f"```{language}")
            
            if removed_lines:
                for line in removed_lines[:5]:
                    improvements.append(line)
            elif added_lines:
                improvements.append("# Previous version")
            
            improvements.append("```")
            improvements.append("")
            improvements.append("**Improved Code:**")
            improvements.append(f"```{language}")
            
            if added_lines:
                for line in added_lines[:5]:
                    if line.strip():
                        improvements.append(line)
            
            improvements.append("```")
            improvements.append("")
            improvements.append("**Why This Is Better:**")
            improvements.append("- Enhanced code structure and readability")
            improvements.append("- Improved maintainability")
            improvements.append("- Better adherence to best practices")
            
            return '\n'.join(improvements)
    
    async def analyze_file_changes(self, file_info: Dict, full_diff: str) -> Dict:
        """Analyze changes in a specific file using YAML prompts"""
        file_path = file_info['filename']
        file_diff = self.extract_file_diff(full_diff, file_path)
        
        # CHANGED: Use the new detailed parsing method
        old_code, new_code, code_changes = self.parse_diff_changes_detailed(file_diff)
        
        language = self.detect_language(file_path)
        
        # Use YAML-based prompt template
        analysis_prompt = self.prompt_manager.get_prompt_template('file_analysis')
        
        try:
            chain = analysis_prompt | self.llm
            analysis = await chain.ainvoke({
                "filename": file_path,
                "language": language,
                "additions": file_info.get('additions', 0),
                "deletions": file_info.get('deletions', 0),
                "old_code": old_code,        # ADDED
                "new_code": new_code,        # ADDED
                "diff": file_diff[:5000],
                "changes_summary": code_changes
            })
            
            improvement_suggestions = await self.generate_code_improvements(file_path, file_diff, language)

            
            return {
                "file": file_path,
                "language": language,
                "analysis": analysis.content,
                "old_code": old_code,        # ADDED
                "new_code": new_code,        # ADDED
                "code_changes": code_changes,
                "improvements": improvement_suggestions,
                "changes": {
                    "additions": file_info.get('additions', 0),
                    "deletions": file_info.get('deletions', 0)
                }
            }
            
        except Exception as e:
            if ConfigService.get_logging_config()['debug_enabled']:
                print(f"❌ Error analyzing file {file_path}: {e}")
            fallback_improvements = self.generate_fallback_improvements(file_path, language, [], [])
            
            return {
                "file": file_path,
                "language": language,
                "analysis": f"Basic analysis for {file_path}: {str(e)}",
                "old_code": old_code if 'old_code' in locals() else "Error extracting old code",  # ADDED
                "new_code": new_code if 'new_code' in locals() else "Error extracting new code",  # ADDED
                "code_changes": code_changes if 'code_changes' in locals() else "Error parsing changes",
                "improvements": fallback_improvements,
                "changes": {
                    "additions": file_info.get('additions', 0),
                    "deletions": file_info.get('deletions', 0)
                }
            }
    
    async def analyze_pr(self, owner: str, repo: str, pr_number: int) -> Dict:
        """Comprehensive PR analysis"""
        try:
            if ConfigService.get_logging_config()['debug_enabled']:
                print(f"🔍 Starting PR analysis for {owner}/{repo}#{pr_number}")
            
            # Get PR data
            pr_details = self.github_service.get_pr_details(owner, repo, pr_number)
            diff = self.github_service.get_pr_diff(owner, repo, pr_number)
            files = self.github_service.get_pr_files(owner, repo, pr_number)
            
            if ConfigService.get_logging_config()['debug_enabled']:
                print(f"📁 Analyzing {len(files)} files...")
            
            # Analyze each file
            file_reviews = []
            for file_info in files[:10]:
                if file_info.get('status') != 'removed':
                    try:
                        file_review = await self.analyze_file_changes(file_info, diff)
                        file_reviews.append(file_review)
                        if ConfigService.get_logging_config()['debug_enabled']:
                            print(f"✅ Analyzed {file_info['filename']}")
                    except Exception as e:
                        if ConfigService.get_logging_config()['debug_enabled']:
                            print(f"⚠️  Error analyzing {file_info.get('filename', 'unknown')}: {e}")
                        file_reviews.append({
                                "file": file_info.get('filename', 'unknown'),
                                "language": self.detect_language(file_info.get('filename', '')),
                                "analysis": f"Could not analyze this file: {str(e)}",
                                "old_code": "Error extracting old code",        
                                "new_code": "Error extracting new code",        # ADD THIS
                                "code_changes": "Analysis failed",
                                "improvements": "Analysis error occurred",
                                "changes": {
                                    "additions": file_info.get('additions', 0),
                                    "deletions": file_info.get('deletions', 0)
                                }
                            })

            
            if ConfigService.get_logging_config()['debug_enabled']:
                print("📊 Generating overall review...")
            
            # Generate overall review
            overall_review = await self.generate_overall_review(pr_details, file_reviews)
            
            # Generate summary
            summary = await self.generate_summary(overall_review, file_reviews)
            
            if ConfigService.get_logging_config()['debug_enabled']:
                print("✅ PR analysis completed")
            
            return {
                "pr_details": pr_details,
                "overall_review": overall_review,
                "file_reviews": file_reviews,
                "summary": summary
            }
            
        except Exception as e:
            if ConfigService.get_logging_config()['debug_enabled']:
                print(f"❌ PR analysis failed: {e}")
            raise Exception(f"PR analysis failed: {str(e)}")
    
    async def generate_overall_review(self, pr_details: Dict, file_reviews: List[Dict]) -> str:
        """Generate comprehensive PR review using YAML prompts"""
        # Use YAML-based prompt template
        review_prompt = self.prompt_manager.get_prompt_template('overall_review')
        
        file_summary = '\n'.join([
            f"- {review['file']} ({review.get('language', 'Unknown')}): {review['changes']['additions']} additions, {review['changes']['deletions']} deletions"
            for review in file_reviews
        ])
        
        try:
            chain = review_prompt | self.llm
            review = await chain.ainvoke({
                "title": pr_details.get('title', ''),
                "description": pr_details.get('body', '')[:1000] if pr_details.get('body') else 'No description',
                "file_analysis": file_summary
            })
            
            return review.content
        except Exception as e:
            if ConfigService.get_logging_config()['debug_enabled']:
                print(f"❌ Error generating overall review: {e}")
            return f"## Basic PR Review\n\nPR: {pr_details.get('title', 'Unknown')}\nFiles analyzed: {len(file_reviews)}\n\nManual review recommended."
    
    async def generate_summary(self, overall_review: str, file_reviews: List[Dict]) -> str:
        """Generate concise summary using YAML prompts"""
        # Use YAML-based prompt template
        summary_prompt = self.prompt_manager.get_prompt_template('summary_generation')
        
        try:
            chain = summary_prompt | self.llm
            summary = await chain.ainvoke({
                "overall": overall_review[:1000],
                "file_count": len(file_reviews)
            })
            
            return summary.content
        except Exception as e:
            if ConfigService.get_logging_config()['debug_enabled']:
                print(f"❌ Error generating summary: {e}")
            return f"Summary: Analyzed {len(file_reviews)} files. Manual review recommended."
    
    def reload_prompts(self):
        """Reload prompts from YAML file (useful for development)"""
        self.prompt_manager.reload_prompts()
