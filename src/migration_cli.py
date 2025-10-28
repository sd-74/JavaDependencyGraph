#!/usr/bin/env python3
"""
Command Line Interface for Java Code Migration Tool

This CLI provides easy access to the headless Java code migration capabilities.
It can process JIRA tickets and perform automated code migrations.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from dependency_graph.migration_engine import MigrationEngine


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Java Code Migration Tool - Automated headless code migrations from JIRA tickets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate from JIRA ticket key (requires JIRA config)
  python migration_cli.py --ticket PROJ-123 --project /path/to/java/project

  # Migrate from raw ticket content
  python migration_cli.py --ticket-file ticket.txt --project /path/to/java/project

  # Preview migration without executing
  python migration_cli.py --preview --ticket-file ticket.txt --project /path/to/java/project

  # Use custom output directory
  python migration_cli.py --ticket PROJ-123 --project /path/to/java/project --output /custom/output

Environment Variables:
  OPENAI_API_KEY: OpenAI API key for LLM integration
  JIRA_BASE_URL: JIRA base URL for API calls
  JIRA_API_TOKEN: JIRA API token for authentication
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--project", 
        required=True,
        help="Path to the Java project to migrate"
    )
    
    # Ticket input (mutually exclusive)
    ticket_group = parser.add_mutually_exclusive_group(required=True)
    ticket_group.add_argument(
        "--ticket",
        help="JIRA ticket key (e.g., PROJ-123) or raw ticket content"
    )
    ticket_group.add_argument(
        "--ticket-file",
        help="Path to file containing JIRA ticket content"
    )
    
    # Optional arguments
    parser.add_argument(
        "--output",
        default="migration_output",
        help="Output directory for migration results (default: migration_output)"
    )
    
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview migration plan without executing"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4",
        help="LLM model to use (default: gpt-4)"
    )
    
    parser.add_argument(
        "--jira-url",
        help="JIRA base URL (overrides JIRA_BASE_URL env var)"
    )
    
    parser.add_argument(
        "--jira-token",
        help="JIRA API token (overrides JIRA_API_TOKEN env var)"
    )
    
    parser.add_argument(
        "--openai-key",
        help="OpenAI API key (overrides OPENAI_API_KEY env var)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate project path
    project_path = Path(args.project)
    if not project_path.exists():
        print(f"❌ Error: Project path does not exist: {project_path}")
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"❌ Error: Project path is not a directory: {project_path}")
        sys.exit(1)
    
    # Get ticket content
    ticket_content = get_ticket_content(args)
    if not ticket_content:
        print("❌ Error: Could not get ticket content")
        sys.exit(1)
    
    # Initialize migration engine
    try:
        engine = MigrationEngine(
            openai_api_key=args.openai_key or os.getenv("OPENAI_API_KEY"),
            jira_base_url=args.jira_url or os.getenv("JIRA_BASE_URL"),
            jira_api_token=args.jira_token or os.getenv("JIRA_API_TOKEN"),
            llm_model=args.model
        )
    except Exception as e:
        print(f"❌ Error initializing migration engine: {e}")
        sys.exit(1)
    
    # Execute migration or preview
    try:
        if args.preview:
            print("🔍 Previewing migration...")
            preview = engine.preview_migration(ticket_content, str(project_path))
            
            if "error" in preview:
                print(f"❌ Preview failed: {preview['error']}")
                sys.exit(1)
            
            print_preview(preview)
        else:
            print("🚀 Starting migration...")
            result = engine.migrate_from_jira_ticket(
                ticket_content, 
                str(project_path), 
                args.output
            )
            
            print_migration_result(result)
            
            if not result.success:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⏹️  Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def get_ticket_content(args) -> Optional[str]:
    """Get ticket content from various sources"""
    if args.ticket:
        return args.ticket
    elif args.ticket_file:
        ticket_file = Path(args.ticket_file)
        if not ticket_file.exists():
            print(f"❌ Error: Ticket file does not exist: {ticket_file}")
            return None
        return ticket_file.read_text()
    return None


def print_preview(preview: dict):
    """Print migration preview information"""
    print("\n" + "="*60)
    print("📋 MIGRATION PREVIEW")
    print("="*60)
    
    # Requirements
    if preview.get("requirements"):
        req = preview["requirements"]
        print(f"\n📝 Ticket: {req.get('ticket_id', 'N/A')}")
        print(f"📝 Title: {req.get('title', 'N/A')}")
        print(f"📝 Type: {req.get('migration_type', 'N/A')}")
        print(f"📝 Priority: {req.get('priority', 'N/A')}")
        print(f"📝 Complexity: {req.get('complexity', 'N/A')}")
        
        if req.get('affected_classes'):
            print(f"📝 Affected Classes: {', '.join(req['affected_classes'])}")
        if req.get('affected_methods'):
            print(f"📝 Affected Methods: {', '.join(req['affected_methods'])}")
    
    # Migration Plan
    if preview.get("migration_plan"):
        plan = preview["migration_plan"]
        print(f"\n🎯 Migration Type: {plan.get('migration_type', 'N/A')}")
        print(f"🎯 Affected Files: {len(plan.get('affected_files', []))}")
        
        if plan.get('transformation_steps'):
            print(f"\n📋 Transformation Steps:")
            for i, step in enumerate(plan['transformation_steps'], 1):
                print(f"  {i}. {step.get('description', 'N/A')}")
                if step.get('file'):
                    print(f"     File: {step['file']}")
                if step.get('action'):
                    print(f"     Action: {step['action']}")
    
    # Function Descriptions
    if preview.get("function_descriptions"):
        print(f"\n🔍 Functions to Analyze: {len(preview['function_descriptions'])}")
        for func in preview['function_descriptions'][:5]:  # Show first 5
            print(f"  • {func.get('name', 'N/A')} ({func.get('class', 'N/A')})")
        if len(preview['function_descriptions']) > 5:
            print(f"  ... and {len(preview['function_descriptions']) - 5} more")
    
    # AST Summary
    if preview.get("ast_summary"):
        ast = preview["ast_summary"]
        print(f"\n📊 Project Analysis:")
        print(f"  • Files: {ast.get('total_files', 0)}")
        print(f"  • Classes: {ast.get('total_classes', 0)}")
        print(f"  • Methods: {ast.get('total_methods', 0)}")
        print(f"  • Dependencies: {ast.get('total_edges', 0)}")
    
    print("\n" + "="*60)


def print_migration_result(result):
    """Print migration result information"""
    print("\n" + "="*60)
    print("📊 MIGRATION RESULT")
    print("="*60)
    
    status = "✅ SUCCESS" if result.success else "❌ FAILED"
    print(f"\n🎯 Status: {status}")
    print(f"🎯 Ticket: {result.ticket_id}")
    
    # Files processed
    print(f"\n📁 Files Processed: {len(result.original_files)}")
    for filename in result.original_files.keys():
        print(f"  • {filename}")
    
    # Migration plan summary
    if result.migration_plan:
        plan = result.migration_plan
        print(f"\n📋 Migration Plan:")
        print(f"  • Type: {plan.migration_type}")
        print(f"  • Steps: {len(plan.transformation_steps)}")
        print(f"  • New Dependencies: {len(plan.new_dependencies)}")
        print(f"  • Removed Dependencies: {len(plan.removed_dependencies)}")
    
    # Validation results
    if result.validation_results:
        print(f"\n✅ Validation Results:")
        for filename, validation in result.validation_results.items():
            is_valid = validation.get('is_valid', False)
            score = validation.get('overall_score', 0)
            print(f"  • {filename}: {'✅' if is_valid else '❌'} (Score: {score})")
            
            if validation.get('compilation_errors'):
                print(f"    Errors: {', '.join(validation['compilation_errors'])}")
    
    # Errors and warnings
    if result.errors:
        print(f"\n❌ Errors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  • {error}")
    
    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  • {warning}")
    
    # Function analysis
    if result.function_descriptions:
        print(f"\n🔍 Functions Analyzed: {len(result.function_descriptions)}")
        for func in result.function_descriptions[:3]:  # Show first 3
            print(f"  • {func.name} ({func.class_name}) - {func.complexity}")
        if len(result.function_descriptions) > 3:
            print(f"  ... and {len(result.function_descriptions) - 3} more")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
