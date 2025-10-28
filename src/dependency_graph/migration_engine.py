"""
Migration Engine for Java Code Migration Tool

This module orchestrates the complete migration process by combining:
1. JIRA ticket parsing
2. AST analysis and dependency extraction
3. LLM-powered function analysis and code generation
4. Migration validation and execution
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from .jira_parser import JiraParser, MigrationRequirement
from .llm_integration import LLMIntegration, FunctionDescription, MigrationPlan
from .dependency_analyzer import Analyzer
from .analyzer import index_repo


@dataclass
class MigrationResult:
    """Result of a complete migration process"""
    ticket_id: str
    success: bool
    original_files: Dict[str, str]  # filename -> content
    migrated_files: Dict[str, str]  # filename -> content
    migration_plan: MigrationPlan
    validation_results: Dict[str, Any]
    function_descriptions: List[FunctionDescription]
    ast_analysis: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


class MigrationEngine:
    """Main engine for orchestrating Java code migrations"""
    
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 jira_base_url: Optional[str] = None,
                 jira_api_token: Optional[str] = None,
                 llm_model: str = "gpt-4"):
        """
        Initialize the migration engine
        
        Args:
            openai_api_key: OpenAI API key for LLM integration
            jira_base_url: JIRA base URL for ticket fetching
            jira_api_token: JIRA API token for authentication
            llm_model: LLM model to use (default: gpt-4)
        """
        self.llm = LLMIntegration(api_key=openai_api_key, model=llm_model)
        self.jira_parser = JiraParser(jira_base_url, jira_api_token)
        self.analyzer = Analyzer()
    
    def migrate_from_jira_ticket(self, 
                                ticket_input: str,
                                java_project_path: str,
                                output_dir: str = "migration_output") -> MigrationResult:
        """
        Complete migration process starting from a JIRA ticket
        
        Args:
            ticket_input: JIRA ticket key or raw ticket content
            java_project_path: Path to the Java project to migrate
            output_dir: Directory to save migration results
            
        Returns:
            MigrationResult with complete migration information
        """
        try:
            # Step 1: Parse JIRA ticket
            print("Step 1: Parsing JIRA ticket...")
            requirements = self._parse_ticket(ticket_input)
            print(f"✓ Parsed ticket: {requirements.ticket_id} - {requirements.title}")
            
            # Step 2: Analyze Java project AST
            print("Step 2: Analyzing Java project structure...")
            ast_analysis = self._analyze_java_project(java_project_path)
            print(f"✓ Analyzed {len(ast_analysis.get('files', []))} Java files")
            
            # Step 3: Extract function descriptions using LLM
            print("Step 3: Analyzing functions with LLM...")
            function_descriptions = self._analyze_functions(ast_analysis, requirements)
            print(f"✓ Analyzed {len(function_descriptions)} functions")
            
            # Step 4: Generate migration plan
            print("Step 4: Generating migration plan...")
            migration_plan = self.llm.generate_migration_plan(
                requirements, ast_analysis, function_descriptions
            )
            print(f"✓ Generated plan with {len(migration_plan.transformation_steps)} steps")
            
            # Step 5: Execute migration
            print("Step 5: Executing migration...")
            migration_result = self._execute_migration(
                requirements, ast_analysis, migration_plan, function_descriptions
            )
            
            # Step 6: Save results
            print("Step 6: Saving migration results...")
            self._save_migration_results(migration_result, output_dir)
            print(f"✓ Migration completed. Results saved to {output_dir}")
            
            return migration_result
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return MigrationResult(
                ticket_id=ticket_input,
                success=False,
                original_files={},
                migrated_files={},
                migration_plan=MigrationPlan("", [], [], [], [], [], []),
                validation_results={},
                function_descriptions=[],
                ast_analysis={},
                errors=[str(e)],
                warnings=[]
            )
    
    def _parse_ticket(self, ticket_input: str) -> MigrationRequirement:
        """Parse JIRA ticket from input"""
        # Check if it looks like a JIRA ticket key
        import re
        if re.match(r'^[A-Z]+-\d+$', ticket_input.strip()):
            return self.jira_parser.parse_ticket_from_api(ticket_input)
        else:
            return self.jira_parser.parse_ticket_from_content(ticket_input)
    
    def _analyze_java_project(self, project_path: str) -> Dict[str, Any]:
        """Analyze Java project and return AST analysis"""
        project_path = Path(project_path)
        
        # Index the repository
        files = index_repo(project_path)
        
        # Run dependency analysis
        self.analyzer.files = files
        self.analyzer.stage1_add_syntactic()
        self.analyzer.stage2_build_symbols()
        self.analyzer.stage3_cha_and_overrides()
        self.analyzer.stage4_calls_and_news()
        
        # Prepare AST analysis summary
        ast_analysis = {
            "files": files,
            "nodes": self.analyzer.nodes,
            "edges": self.analyzer.edges,
            "classes": [f for f in files for t in f["symbols"]["types"]],
            "methods": [f for f in files for m in f["symbols"]["methods"]],
            "statements": [f for f in files for s in f["symbols"]["stmts"]],
            "class_hierarchy": self.analyzer.parents,
            "method_index": self.analyzer.methods_index
        }
        
        return ast_analysis
    
    def _analyze_functions(self, 
                          ast_analysis: Dict[str, Any], 
                          requirements: MigrationRequirement) -> List[FunctionDescription]:
        """Analyze functions using LLM to get detailed descriptions"""
        function_descriptions = []
        
        # Focus on files mentioned in requirements or affected classes
        target_files = set(requirements.target_files)
        if requirements.affected_classes:
            # Find files containing affected classes
            for file_data in ast_analysis["files"]:
                for class_info in file_data["symbols"]["types"]:
                    if class_info["name"] in requirements.affected_classes:
                        target_files.add(Path(file_data["path"]).name)
        
        # Analyze each target file
        for file_data in ast_analysis["files"]:
            file_path = Path(file_data["path"])
            if file_path.name in target_files:
                java_code = file_path.read_text()
                package = file_data["symbols"]["package"]
                
                for class_info in file_data["symbols"]["types"]:
                    class_name = class_info["name"]
                    if not requirements.affected_classes or class_name in requirements.affected_classes:
                        descriptions = self.llm.analyze_function_descriptions(
                            java_code, class_name, package
                        )
                        function_descriptions.extend(descriptions)
        
        return function_descriptions
    
    def _execute_migration(self, 
                          requirements: MigrationRequirement,
                          ast_analysis: Dict[str, Any],
                          migration_plan: MigrationPlan,
                          function_descriptions: List[FunctionDescription]) -> MigrationResult:
        """Execute the migration plan and generate migrated code"""
        original_files = {}
        migrated_files = {}
        errors = []
        warnings = []
        
        try:
            # Process each file mentioned in the migration plan
            for file_name in migration_plan.affected_files:
                # Find the file in the project
                file_path = self._find_file_in_project(file_name, ast_analysis["files"])
                if not file_path:
                    errors.append(f"File {file_name} not found in project")
                    continue
                
                # Read original content
                original_content = file_path.read_text()
                original_files[file_name] = original_content
                
                # Generate migrated content
                migrated_content = self.llm.generate_migrated_code(
                    original_content, migration_plan, function_descriptions
                )
                migrated_files[file_name] = migrated_content
            
            # Validate migration
            validation_results = {}
            for file_name, migrated_content in migrated_files.items():
                original_content = original_files.get(file_name, "")
                validation = self.llm.validate_migration(
                    original_content, migrated_content, migration_plan
                )
                validation_results[file_name] = validation
                
                if not validation.get("is_valid", False):
                    errors.extend(validation.get("issues_found", []))
                else:
                    warnings.extend(validation.get("suggestions", []))
            
            return MigrationResult(
                ticket_id=requirements.ticket_id,
                success=len(errors) == 0,
                original_files=original_files,
                migrated_files=migrated_files,
                migration_plan=migration_plan,
                validation_results=validation_results,
                function_descriptions=function_descriptions,
                ast_analysis=ast_analysis,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            errors.append(f"Migration execution failed: {str(e)}")
            return MigrationResult(
                ticket_id=requirements.ticket_id,
                success=False,
                original_files=original_files,
                migrated_files=migrated_files,
                migration_plan=migration_plan,
                validation_results={},
                function_descriptions=function_descriptions,
                ast_analysis=ast_analysis,
                errors=errors,
                warnings=warnings
            )
    
    def _find_file_in_project(self, file_name: str, files: List[Dict]) -> Optional[Path]:
        """Find a file in the project by name"""
        for file_data in files:
            file_path = Path(file_data["path"])
            if file_path.name == file_name:
                return file_path
        return None
    
    def _save_migration_results(self, result: MigrationResult, output_dir: str):
        """Save migration results to files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save original files
        original_dir = output_path / "original"
        original_dir.mkdir(exist_ok=True)
        for filename, content in result.original_files.items():
            (original_dir / filename).write_text(content)
        
        # Save migrated files
        migrated_dir = output_path / "migrated"
        migrated_dir.mkdir(exist_ok=True)
        for filename, content in result.migrated_files.items():
            (migrated_dir / filename).write_text(content)
        
        # Save migration metadata
        metadata = {
            "ticket_id": result.ticket_id,
            "success": result.success,
            "migration_plan": asdict(result.migration_plan),
            "validation_results": result.validation_results,
            "function_descriptions": [asdict(f) for f in result.function_descriptions],
            "errors": result.errors,
            "warnings": result.warnings,
            "files_processed": list(result.original_files.keys())
        }
        
        (output_path / "migration_metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False)
        )
        
        # Save AST analysis summary
        ast_summary = {
            "total_files": len(result.ast_analysis.get("files", [])),
            "total_classes": len(result.ast_analysis.get("classes", [])),
            "total_methods": len(result.ast_analysis.get("methods", [])),
            "total_edges": len(result.ast_analysis.get("edges", [])),
            "class_hierarchy": result.ast_analysis.get("class_hierarchy", {})
        }
        
        (output_path / "ast_analysis.json").write_text(
            json.dumps(ast_summary, indent=2, ensure_ascii=False)
        )
    
    def preview_migration(self, 
                         ticket_input: str,
                         java_project_path: str) -> Dict[str, Any]:
        """
        Preview what the migration would do without actually executing it
        
        Args:
            ticket_input: JIRA ticket key or raw ticket content
            java_project_path: Path to the Java project
            
        Returns:
            Dictionary with migration preview information
        """
        try:
            # Parse ticket and analyze project
            requirements = self._parse_ticket(ticket_input)
            ast_analysis = self._analyze_java_project(java_project_path)
            function_descriptions = self._analyze_functions(ast_analysis, requirements)
            
            # Generate migration plan
            migration_plan = self.llm.generate_migration_plan(
                requirements, ast_analysis, function_descriptions
            )
            
            return {
                "requirements": asdict(requirements),
                "migration_plan": asdict(migration_plan),
                "affected_files": migration_plan.affected_files,
                "transformation_steps": migration_plan.transformation_steps,
                "function_descriptions": [asdict(f) for f in function_descriptions],
                "ast_summary": {
                    "total_files": len(ast_analysis.get("files", [])),
                    "total_classes": len(ast_analysis.get("classes", [])),
                    "total_methods": len(ast_analysis.get("methods", [])),
                    "total_edges": len(ast_analysis.get("edges", []))
                }
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "requirements": None,
                "migration_plan": None,
                "affected_files": [],
                "transformation_steps": [],
                "function_descriptions": [],
                "ast_summary": {}
            }
