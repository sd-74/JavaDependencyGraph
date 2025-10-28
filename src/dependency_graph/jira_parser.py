"""
JIRA Ticket Parser for Java Code Migration Tool

This module parses JIRA tickets to extract migration requirements and context.
It can handle both direct JIRA API calls and manual ticket content input.
"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import requests
from urllib.parse import urljoin


@dataclass
class MigrationRequirement:
    """Structured representation of migration requirements from a JIRA ticket"""
    ticket_id: str
    title: str
    description: str
    migration_type: str  # e.g., "refactor", "upgrade", "deprecation", "security"
    target_files: List[str]  # Java files mentioned in the ticket
    affected_classes: List[str]  # Classes that need to be modified
    affected_methods: List[str]  # Methods that need to be modified
    migration_goals: List[str]  # Specific goals extracted from description
    constraints: List[str]  # Any constraints or requirements
    priority: str  # High, Medium, Low
    complexity: str  # Simple, Medium, Complex


class JiraParser:
    """Parser for JIRA tickets to extract migration requirements"""
    
    def __init__(self, jira_base_url: Optional[str] = None, api_token: Optional[str] = None):
        self.jira_base_url = jira_base_url
        self.api_token = api_token
        self.session = requests.Session()
        if api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            })
    
    def parse_ticket_from_api(self, ticket_key: str) -> MigrationRequirement:
        """Fetch and parse a JIRA ticket from the API"""
        if not self.jira_base_url or not self.api_token:
            raise ValueError("JIRA base URL and API token are required for API calls")
        
        url = urljoin(self.jira_base_url, f"/rest/api/3/issue/{ticket_key}")
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        return self._parse_ticket_data(data)
    
    def parse_ticket_from_content(self, ticket_content: str, ticket_id: str = "MANUAL") -> MigrationRequirement:
        """Parse a JIRA ticket from raw content (for manual input)"""
        # This is a simplified parser for manual content
        # In a real implementation, you might want to parse JIRA markup
        lines = ticket_content.split('\n')
        
        title = ""
        description = ""
        in_description = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('Summary:') or line.startswith('Title:'):
                title = line.split(':', 1)[1].strip()
            elif line.startswith('Description:') or line.startswith('Details:'):
                in_description = True
                description = line.split(':', 1)[1].strip()
            elif in_description and line:
                description += " " + line
            elif line.startswith('Priority:'):
                priority = line.split(':', 1)[1].strip()
            elif line.startswith('Type:'):
                migration_type = line.split(':', 1)[1].strip()
        
        return self._extract_requirements_from_text(ticket_id, title, description)
    
    def _parse_ticket_data(self, data: Dict[str, Any]) -> MigrationRequirement:
        """Parse JIRA API response data"""
        fields = data.get('fields', {})
        ticket_id = data.get('key', 'UNKNOWN')
        title = fields.get('summary', '')
        description = fields.get('description', '')
        
        # Extract description text from JIRA markup
        if isinstance(description, dict):
            description = description.get('content', [])
            description = self._extract_text_from_jira_content(description)
        
        return self._extract_requirements_from_text(ticket_id, title, description)
    
    def _extract_text_from_jira_content(self, content: List[Dict]) -> str:
        """Extract plain text from JIRA content structure"""
        text_parts = []
        
        def extract_text_recursive(node):
            if isinstance(node, dict):
                if node.get('type') == 'text':
                    text_parts.append(node.get('text', ''))
                elif 'content' in node:
                    for child in node['content']:
                        extract_text_recursive(child)
            elif isinstance(node, list):
                for child in node:
                    extract_text_recursive(child)
        
        extract_text_recursive(content)
        return ' '.join(text_parts)
    
    def _extract_requirements_from_text(self, ticket_id: str, title: str, description: str) -> MigrationRequirement:
        """Extract migration requirements from ticket text using pattern matching"""
        full_text = f"{title} {description}".lower()
        
        # Extract migration type
        migration_type = self._extract_migration_type(full_text)
        
        # Extract target files (Java files mentioned)
        target_files = self._extract_java_files(full_text)
        
        # Extract affected classes and methods
        affected_classes = self._extract_classes(full_text)
        affected_methods = self._extract_methods(full_text)
        
        # Extract migration goals
        migration_goals = self._extract_migration_goals(full_text)
        
        # Extract constraints
        constraints = self._extract_constraints(full_text)
        
        # Determine priority and complexity
        priority = self._determine_priority(full_text)
        complexity = self._determine_complexity(full_text, len(affected_classes), len(affected_methods))
        
        return MigrationRequirement(
            ticket_id=ticket_id,
            title=title,
            description=description,
            migration_type=migration_type,
            target_files=target_files,
            affected_classes=affected_classes,
            affected_methods=affected_methods,
            migration_goals=migration_goals,
            constraints=constraints,
            priority=priority,
            complexity=complexity
        )
    
    def _extract_migration_type(self, text: str) -> str:
        """Extract the type of migration from the text"""
        patterns = {
            'refactor': ['refactor', 'restructure', 'reorganize', 'clean up'],
            'upgrade': ['upgrade', 'update', 'migrate to', 'version'],
            'deprecation': ['deprecate', 'remove', 'obsolete', 'legacy'],
            'security': ['security', 'vulnerability', 'patch', 'fix'],
            'performance': ['performance', 'optimize', 'speed up', 'memory'],
            'feature': ['feature', 'add', 'implement', 'new functionality']
        }
        
        for migration_type, keywords in patterns.items():
            if any(keyword in text for keyword in keywords):
                return migration_type
        
        return 'general'
    
    def _extract_java_files(self, text: str) -> List[str]:
        """Extract Java file names from the text"""
        # Look for .java file references
        java_file_pattern = r'(\w+\.java)'
        files = re.findall(java_file_pattern, text)
        
        # Also look for class names that might be files
        class_pattern = r'class\s+(\w+)'
        classes = re.findall(class_pattern, text)
        
        # Convert class names to potential file names
        potential_files = [f"{cls}.java" for cls in classes]
        
        return list(set(files + potential_files))
    
    def _extract_classes(self, text: str) -> List[str]:
        """Extract Java class names from the text"""
        # Look for class declarations and references
        class_patterns = [
            r'class\s+(\w+)',
            r'public\s+class\s+(\w+)',
            r'private\s+class\s+(\w+)',
            r'protected\s+class\s+(\w+)',
            r'extends\s+(\w+)',
            r'implements\s+(\w+)',
            r'new\s+(\w+)\(',
            r'(\w+)\.class'
        ]
        
        classes = set()
        for pattern in class_patterns:
            matches = re.findall(pattern, text)
            classes.update(matches)
        
        return list(classes)
    
    def _extract_methods(self, text: str) -> List[str]:
        """Extract Java method names from the text"""
        # Look for method declarations and calls
        method_patterns = [
            r'(\w+)\s*\([^)]*\)\s*\{',  # method declarations
            r'(\w+)\s*\([^)]*\)\s*;',   # method calls
            r'\.(\w+)\s*\(',            # method calls with dot notation
            r'public\s+\w+\s+(\w+)\s*\(',  # public method declarations
            r'private\s+\w+\s+(\w+)\s*\(', # private method declarations
            r'protected\s+\w+\s+(\w+)\s*\(' # protected method declarations
        ]
        
        methods = set()
        for pattern in method_patterns:
            matches = re.findall(pattern, text)
            methods.update(matches)
        
        return list(methods)
    
    def _extract_migration_goals(self, text: str) -> List[str]:
        """Extract specific migration goals from the text"""
        goal_keywords = [
            'replace', 'update', 'modify', 'change', 'convert',
            'improve', 'enhance', 'fix', 'resolve', 'implement',
            'remove', 'add', 'delete', 'rename', 'move'
        ]
        
        goals = []
        sentences = re.split(r'[.!?]', text)
        
        for sentence in sentences:
            if any(keyword in sentence for keyword in goal_keywords):
                goals.append(sentence.strip())
        
        return goals[:5]  # Limit to top 5 goals
    
    def _extract_constraints(self, text: str) -> List[str]:
        """Extract constraints and requirements from the text"""
        constraint_keywords = [
            'must', 'should', 'cannot', 'avoid', 'maintain',
            'preserve', 'keep', 'ensure', 'guarantee', 'require'
        ]
        
        constraints = []
        sentences = re.split(r'[.!?]', text)
        
        for sentence in sentences:
            if any(keyword in sentence for keyword in constraint_keywords):
                constraints.append(sentence.strip())
        
        return constraints[:3]  # Limit to top 3 constraints
    
    def _determine_priority(self, text: str) -> str:
        """Determine priority based on text content"""
        high_priority_keywords = ['urgent', 'critical', 'blocking', 'immediate', 'asap']
        medium_priority_keywords = ['important', 'soon', 'priority']
        
        if any(keyword in text for keyword in high_priority_keywords):
            return 'High'
        elif any(keyword in text for keyword in medium_priority_keywords):
            return 'Medium'
        else:
            return 'Low'
    
    def _determine_complexity(self, text: str, num_classes: int, num_methods: int) -> str:
        """Determine complexity based on text content and affected elements"""
        complex_keywords = ['complex', 'major', 'extensive', 'comprehensive', 'complete']
        
        if any(keyword in text for keyword in complex_keywords) or num_classes > 10 or num_methods > 20:
            return 'Complex'
        elif num_classes > 5 or num_methods > 10:
            return 'Medium'
        else:
            return 'Simple'


def parse_jira_ticket(ticket_input: str, jira_config: Optional[Dict[str, str]] = None) -> MigrationRequirement:
    """
    Convenience function to parse a JIRA ticket from various input formats
    
    Args:
        ticket_input: Either a JIRA ticket key (e.g., "PROJ-123") or raw ticket content
        jira_config: Optional dict with 'base_url' and 'api_token' for API calls
    
    Returns:
        MigrationRequirement object with extracted information
    """
    parser = JiraParser()
    
    # Check if input looks like a JIRA ticket key
    if re.match(r'^[A-Z]+-\d+$', ticket_input.strip()):
        if jira_config and 'base_url' in jira_config and 'api_token' in jira_config:
            parser = JiraParser(jira_config['base_url'], jira_config['api_token'])
            return parser.parse_ticket_from_api(ticket_input)
        else:
            raise ValueError("JIRA configuration required for API calls")
    else:
        # Treat as raw content
        return parser.parse_ticket_from_content(ticket_input)
