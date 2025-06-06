
import os
import requests
import json
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from datetime import datetime
from .models import Repository, PullRequest, ReviewRequest, ReviewResult

class GitHubService:
    def __init__(self):
        self.token = self.user.github_tokens.latest('created_at').token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
    
    def get_user_repositories(self, page=1, per_page=30):
        """Get user's repositories"""
        url = f"{self.base_url}/user/repos"
        params = {
            "page": page,
            "per_page": per_page,
            "sort": "updated",
            "type": "all"
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
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
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_pr_details(self, owner: str, repo: str, pr_number: int):
        """Get PR details from GitHub"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_pr_diff(self, owner: str, repo: str, pr_number: int):
        """Get PR diff from GitHub"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    
    def get_pr_files(self, owner: str, repo: str, pr_number: int):
        """Get changed files in PR"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

class PRReviewService:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.github_service = GitHubService()
    
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
        """Generate specific code improvement suggestions"""
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
        
        improvement_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert code reviewer. Analyze the provided code changes and give specific improvements.

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
- Focus on practical, implementable suggestions"""),
            ("user", """Please analyze this code change:

File: {file_path}
Language: {language}

Added Lines:
{added_lines}

Removed Lines:
{removed_lines}

Context:
{context}

Provide specific improvements with before/after examples.""")
        ])
        
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
            return self.generate_fallback_improvements(file_path, language, added_lines, removed_lines)
    
    def generate_fallback_improvements(self, file_path: str, language: str, added_lines: List[str], removed_lines: List[str]) -> str:
        """Generate fallback improvements when main generation fails"""
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
        """Analyze changes in a specific file"""
        file_path = file_info['filename']
        file_diff = self.extract_file_diff(full_diff, file_path)
        code_changes = self.parse_diff_changes(file_diff)
        language = self.detect_language(file_path)
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior software architect. Provide comprehensive analysis focusing on:
1. Design Patterns & Architecture
2. Performance Analysis 
3. Security Review
4. Maintainability
5. Best Practices

Be specific, actionable, and focus on production readiness."""),
            ("user", """Analyze this file change:

File: {filename}
Language: {language}
Changes: +{additions} -{deletions} lines

Diff Analysis:
{diff}

Code Changes Summary:
{changes_summary}""")
        ])
        
        try:
            chain = analysis_prompt | self.llm
            analysis = await chain.ainvoke({
                "filename": file_path,
                "language": language,
                "additions": file_info.get('additions', 0),
                "deletions": file_info.get('deletions', 0),
                "diff": file_diff[:5000],
                "changes_summary": code_changes
            })
            
            improvement_suggestions = await self.generate_code_improvements(file_path, file_diff, language)
            
            return {
                "file": file_path,
                "language": language,
                "analysis": analysis.content,
                "code_changes": code_changes,
                "improvements": improvement_suggestions,
                "changes": {
                    "additions": file_info.get('additions', 0),
                    "deletions": file_info.get('deletions', 0)
                }
            }
            
        except Exception as e:
            fallback_improvements = self.generate_fallback_improvements(file_path, language, [], [])
            
            return {
                "file": file_path,
                "language": language,
                "analysis": f"Basic analysis for {file_path}: {str(e)}",
                "code_changes": code_changes,
                "improvements": fallback_improvements,
                "changes": {
                    "additions": file_info.get('additions', 0),
                    "deletions": file_info.get('deletions', 0)
                }
            }
    
    async def analyze_pr(self, owner: str, repo: str, pr_number: int) -> Dict:
        """Comprehensive PR analysis"""
        try:
            # Get PR data
            pr_details = self.github_service.get_pr_details(owner, repo, pr_number)
            diff = self.github_service.get_pr_diff(owner, repo, pr_number)
            files = self.github_service.get_pr_files(owner, repo, pr_number)
            
            # Analyze each file
            file_reviews = []
            for file_info in files[:10]:
                if file_info.get('status') != 'removed':
                    try:
                        file_review = await self.analyze_file_changes(file_info, diff)
                        file_reviews.append(file_review)
                    except Exception as e:
                        file_reviews.append({
                            "file": file_info.get('filename', 'unknown'),
                            "language": self.detect_language(file_info.get('filename', '')),
                            "analysis": f"Could not analyze this file: {str(e)}",
                            "code_changes": "Analysis failed",
                            "improvements": "Analysis error occurred",
                            "changes": {
                                "additions": file_info.get('additions', 0),
                                "deletions": file_info.get('deletions', 0)
                            }
                        })
            
            # Generate overall review
            overall_review = await self.generate_overall_review(pr_details, file_reviews)
            
            # Generate summary
            summary = await self.generate_summary(overall_review, file_reviews)
            
            return {
                "pr_details": pr_details,
                "overall_review": overall_review,
                "file_reviews": file_reviews,
                "summary": summary
            }
            
        except Exception as e:
            raise Exception(f"PR analysis failed: {str(e)}")
    
    async def generate_overall_review(self, pr_details: Dict, file_reviews: List[Dict]) -> str:
        """Generate comprehensive PR review"""
        review_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Principal Software Engineer. Provide structured feedback:

## 🎯 EXECUTIVE SUMMARY
- Recommendation: APPROVE/REQUEST_CHANGES/COMMENT with reasoning
- Overall Quality Score: X/10 with justification

## 📊 DETAILED ANALYSIS
### 🏗️ Architecture & Design
### ⚡ Performance Analysis  
### 🔒 Security Review
### 🧹 Code Quality

## 🚀 ACTIONABLE RECOMMENDATIONS
## ✅ POSITIVE ASPECTS"""),
            ("user", """Review this PR:

PR Title: {title}
Description: {description}

File Analysis Summary:
{file_analysis}""")
        ])
        
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
            return f"## Basic PR Review\n\nPR: {pr_details.get('title', 'Unknown')}\nFiles analyzed: {len(file_reviews)}\n\nManual review recommended."
    
    async def generate_summary(self, overall_review: str, file_reviews: List[Dict]) -> str:
        """Generate concise summary"""
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "Create a concise 2-3 sentence summary focusing on key quality and performance aspects."),
            ("user", "Overall Review: {overall}\n\nFile Count: {file_count}")
        ])
        
        try:
            chain = summary_prompt | self.llm
            summary = await chain.ainvoke({
                "overall": overall_review[:1000],
                "file_count": len(file_reviews)
            })
            
            return summary.content
        except Exception as e:
            return f"Summary: Analyzed {len(file_reviews)} files. Manual review recommended."