"""
LLM Integration for Java Code Migration Tool

This module provides integration with Large Language Models for:
1. Analyzing function descriptions and code context
2. Generating migration code based on requirements and AST analysis
3. Providing intelligent code transformation suggestions
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from together import Together
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class FunctionDescription:
    """Structured description of a Java function/method"""
    name: str
    class_name: str
    package: str
    signature: str
    description: str
    parameters: List[Dict[str, str]]  # [{"name": "param1", "type": "String", "description": "..."}]
    return_type: str
    return_description: str
    complexity: str  # Simple, Medium, Complex
    dependencies: List[str]  # Other methods/classes this function depends on
    side_effects: List[str]  # What this function modifies or affects
    usage_context: str  # How this function is typically used


@dataclass
class MigrationPlan:
    """Structured plan for code migration"""
    migration_type: str
    affected_files: List[str]
    transformation_steps: List[Dict[str, Any]]
    new_dependencies: List[str]
    removed_dependencies: List[str]
    validation_checks: List[str]
    rollback_plan: List[str]


class LLMIntegration:
    """Integration with Large Language Models for code analysis and generation"""

    def __init__(self, api_key: Optional[str] = None, model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"):
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("Together.ai API key is required. Set TOGETHER_API_KEY environment variable or pass api_key parameter.")

        self.client = Together(api_key=self.api_key)
        self.model = model
    
    def analyze_function_descriptions(self, 
                                    java_code: str, 
                                    class_name: str, 
                                    package: str) -> List[FunctionDescription]:
        """
        Analyze Java code and generate detailed function descriptions using LLM
        
        Args:
            java_code: The Java source code to analyze
            class_name: Name of the class being analyzed
            package: Package name of the class
            
        Returns:
            List of FunctionDescription objects
        """
        prompt = f"""
        Analyze the following Java code and provide detailed descriptions for each method/function.
        Focus on understanding what each method does, its parameters, return values, and dependencies.

        Package: {package}
        Class: {class_name}

        Java Code:
        ```java
        {java_code}
        ```

        For each method, provide:
        1. Method name and signature
        2. Clear description of what the method does
        3. Parameter descriptions (name, type, purpose)
        4. Return type and what it represents
        5. Complexity level (Simple/Medium/Complex)
        6. Dependencies on other methods or classes
        7. Side effects (what it modifies)
        8. Usage context

        Return the response as a JSON array with this structure:
        [
            {{
                "name": "methodName",
                "signature": "full signature",
                "description": "what this method does",
                "parameters": [
                    {{"name": "param1", "type": "String", "description": "description"}}
                ],
                "return_type": "String",
                "return_description": "what this returns",
                "complexity": "Simple|Medium|Complex",
                "dependencies": ["otherMethod1", "otherClass.method2"],
                "side_effects": ["modifies field X", "calls external service"],
                "usage_context": "typically used for..."
            }}
        ]
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Java code analyzer. Provide detailed, accurate analysis of Java methods and their functionality."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            # Extract JSON from the response
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start != -1 and json_end != -1:
                json_content = content[json_start:json_end]
                method_data = json.loads(json_content)
                
                descriptions = []
                for method in method_data:
                    descriptions.append(FunctionDescription(
                        name=method.get('name', ''),
                        class_name=class_name,
                        package=package,
                        signature=method.get('signature', ''),
                        description=method.get('description', ''),
                        parameters=method.get('parameters', []),
                        return_type=method.get('return_type', 'void'),
                        return_description=method.get('return_description', ''),
                        complexity=method.get('complexity', 'Simple'),
                        dependencies=method.get('dependencies', []),
                        side_effects=method.get('side_effects', []),
                        usage_context=method.get('usage_context', '')
                    ))
                
                return descriptions
            else:
                raise ValueError("Could not extract JSON from LLM response")
                
        except Exception as e:
            print(f"Error analyzing function descriptions: {e}")
            return []
    
    def generate_migration_plan(self, 
                              requirements,
                              ast_analysis: Dict[str, Any],
                              function_descriptions: List[FunctionDescription]) -> MigrationPlan:
        """
        Generate a detailed migration plan based on requirements, AST analysis, and function descriptions
        
        Args:
            requirements: Migration requirements from JIRA ticket
            ast_analysis: AST analysis results from dependency analyzer
            function_descriptions: Detailed function descriptions
            
        Returns:
            MigrationPlan object with step-by-step migration instructions
        """
        prompt = f"""
        Create a detailed migration plan for the following Java code migration task.

        MIGRATION REQUIREMENTS:
        - Ticket ID: {requirements.ticket_id}
        - Title: {requirements.title}
        - Migration Type: {requirements.migration_type}
        - Affected Classes: {', '.join(requirements.affected_classes)}
        - Affected Methods: {', '.join(requirements.affected_methods)}
        - Goals: {', '.join(requirements.migration_goals)}
        - Constraints: {', '.join(requirements.constraints)}

        AST ANALYSIS SUMMARY:
        - Total Classes: {len(ast_analysis.get('classes', []))}
        - Total Methods: {len(ast_analysis.get('methods', []))}
        - Dependencies: {len(ast_analysis.get('edges', []))}

        FUNCTION DESCRIPTIONS:
        {json.dumps([{
            'name': f.name,
            'class': f.class_name,
            'signature': f.signature,
            'description': f.description,
            'complexity': f.complexity,
            'dependencies': f.dependencies
        } for f in function_descriptions], indent=2)}

        Create a comprehensive migration plan that includes:
        1. Step-by-step transformation instructions
        2. New dependencies that need to be added
        3. Dependencies that can be removed
        4. Validation checks to ensure correctness
        5. Rollback plan in case of issues

        Return the response as JSON with this structure:
        {{
            "migration_type": "refactor|upgrade|deprecation|security|performance|feature",
            "affected_files": ["file1.java", "file2.java"],
            "transformation_steps": [
                {{
                    "step": 1,
                    "description": "what to do",
                    "file": "target file",
                    "action": "add|modify|remove|replace",
                    "details": "specific implementation details"
                }}
            ],
            "new_dependencies": ["new.package.Class", "another.dependency"],
            "removed_dependencies": ["old.package.Class", "deprecated.method"],
            "validation_checks": [
                "check that new method signature matches",
                "verify all tests pass",
                "ensure backward compatibility"
            ],
            "rollback_plan": [
                "revert changes to file1.java",
                "restore original method signatures",
                "remove new dependencies"
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Java migration specialist. Create detailed, actionable migration plans that are safe and comprehensive."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            # Extract JSON from the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_content = content[json_start:json_end]
                plan_data = json.loads(json_content)
                
                return MigrationPlan(
                    migration_type=plan_data.get('migration_type', requirements.migration_type),
                    affected_files=plan_data.get('affected_files', []),
                    transformation_steps=plan_data.get('transformation_steps', []),
                    new_dependencies=plan_data.get('new_dependencies', []),
                    removed_dependencies=plan_data.get('removed_dependencies', []),
                    validation_checks=plan_data.get('validation_checks', []),
                    rollback_plan=plan_data.get('rollback_plan', [])
                )
            else:
                raise ValueError("Could not extract JSON from LLM response")
                
        except Exception as e:
            print(f"Error generating migration plan: {e}")
            return MigrationPlan(
                migration_type=requirements.migration_type,
                affected_files=requirements.target_files,
                transformation_steps=[],
                new_dependencies=[],
                removed_dependencies=[],
                validation_checks=[],
                rollback_plan=[]
            )
    
    def generate_migrated_code(self, 
                             original_code: str,
                             migration_plan: MigrationPlan,
                             function_descriptions: List[FunctionDescription]) -> str:
        """
        Generate the actual migrated code based on the migration plan
        
        Args:
            original_code: The original Java code
            migration_plan: Detailed migration plan
            function_descriptions: Function descriptions for context
            
        Returns:
            The migrated Java code
        """
        prompt = f"""
        Generate the migrated Java code based on the following migration plan.

        ORIGINAL CODE:
        ```java
        {original_code}
        ```

        MIGRATION PLAN:
        {json.dumps({
            'migration_type': migration_plan.migration_type,
            'transformation_steps': migration_plan.transformation_steps,
            'new_dependencies': migration_plan.new_dependencies,
            'removed_dependencies': migration_plan.removed_dependencies
        }, indent=2)}

        FUNCTION CONTEXT:
        {json.dumps([{
            'name': f.name,
            'signature': f.signature,
            'description': f.description,
            'dependencies': f.dependencies
        } for f in function_descriptions], indent=2)}

        Apply the migration plan step by step and generate the complete migrated code.
        Ensure that:
        1. All transformation steps are applied correctly
        2. New dependencies are properly imported
        3. Old dependencies are removed
        4. Code compiles and follows Java best practices
        5. Original functionality is preserved
        6. New functionality is properly implemented

        Return only the migrated Java code without any explanations or markdown formatting.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Java developer. Generate clean, compilable, and well-structured Java code that follows best practices."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating migrated code: {e}")
            return original_code  # Return original code if migration fails
    
    def generate_knowledge_graph_dot(self,
                                     function_descriptions: List[FunctionDescription],
                                     title: str = "Java Project Knowledge Graph") -> str:
        """
        Use the LLM to transform function descriptions into a Graphviz DOT diagram.

        Args:
            function_descriptions: List of FunctionDescription objects previously produced by the LLM.
            title: Optional graph title.

        Returns:
            A Graphviz DOT string.
        """
        if not function_descriptions:
            raise ValueError("No function descriptions provided for knowledge graph generation.")

        payload = [{
            "id": f"{f.class_name}.{f.name}",
            "class": f.class_name,
            "package": f.package,
            "signature": f.signature,
            "description": f.description,
            "dependencies": f.dependencies,
            "side_effects": f.side_effects,
            "usage_context": f.usage_context,
            "complexity": f.complexity
        } for f in function_descriptions]

        prompt = f"""
        You are a software architect who creates knowledge graphs of Java projects.
        Given the following JSON data describing methods, produce a Graphviz DOT diagram
        called "{title}" that shows:
        - A node for each method with a concise label containing the method name and class.
        - Cluster subgraphs for each class containing its methods.
        - Directed edges for dependencies listed in the JSON (e.g., Method A -> Method B).
        - Use safe DOT identifiers (alphanumeric and underscores). You may replace dots with underscores.
        - Include edge labels indicating "depends on".
        - Keep the DOT output succinct and valid so it can be rendered without modification.

        JSON data:
        {json.dumps(payload, indent=2)}

        Return ONLY the Graphviz DOT source code, optionally wrapped in a ```dot code block.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at summarizing software systems as Graphviz knowledge graphs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1200
            )

            content = response.choices[0].message.content.strip()

            if "```" in content:
                parts = content.split("```")
                # parts: ['', 'dot', 'digraph...', ''] or similar
                for i in range(len(parts) - 1):
                    snippet = parts[i + 1]
                    if snippet.startswith("dot"):
                        dot_text = parts[i + 2] if i + 2 < len(parts) else ""
                        return dot_text.strip()
                # fallback: take first fenced content
                return parts[1].strip()

            # Fallback: attempt to locate digraph directly
            idx = content.find("digraph")
            if idx != -1:
                return content[idx:].strip()

            raise ValueError("LLM response did not contain Graphviz DOT output.")

        except Exception as e:
            raise RuntimeError(f"Error generating knowledge graph DOT: {e}") from e
    
    def validate_migration(self, 
                         original_code: str, 
                         migrated_code: str,
                         migration_plan: MigrationPlan) -> Dict[str, Any]:
        """
        Validate that the migration was successful
        
        Args:
            original_code: Original Java code
            migrated_code: Migrated Java code
            migration_plan: The migration plan that was applied
            
        Returns:
            Dictionary with validation results
        """
        prompt = f"""
        Validate the following Java code migration to ensure it was successful.

        ORIGINAL CODE:
        ```java
        {original_code}
        ```

        MIGRATED CODE:
        ```java
        {migrated_code}
        ```

        MIGRATION PLAN:
        {json.dumps(migration_plan.transformation_steps, indent=2)}

        VALIDATION CHECKS:
        {', '.join(migration_plan.validation_checks)}

        Please validate:
        1. All transformation steps were applied correctly
        2. Code compiles without syntax errors
        3. Original functionality is preserved
        4. New functionality is properly implemented
        5. Dependencies are correctly updated
        6. Code follows Java best practices

        Return a JSON response with this structure:
        {{
            "is_valid": true/false,
            "compilation_errors": ["error1", "error2"],
            "functionality_preserved": true/false,
            "migration_steps_completed": [1, 2, 3],
            "issues_found": ["issue1", "issue2"],
            "suggestions": ["suggestion1", "suggestion2"],
            "overall_score": 85
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Java code reviewer. Provide thorough validation of code migrations with specific feedback."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            # Extract JSON from the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_content = content[json_start:json_end]
                return json.loads(json_content)
            else:
                return {
                    "is_valid": False,
                    "compilation_errors": ["Could not parse validation response"],
                    "functionality_preserved": False,
                    "migration_steps_completed": [],
                    "issues_found": ["Validation failed"],
                    "suggestions": ["Check LLM response format"],
                    "overall_score": 0
                }
                
        except Exception as e:
            print(f"Error validating migration: {e}")
            return {
                "is_valid": False,
                "compilation_errors": [str(e)],
                "functionality_preserved": False,
                "migration_steps_completed": [],
                "issues_found": ["Validation error"],
                "suggestions": ["Check LLM integration"],
                "overall_score": 0
            }
