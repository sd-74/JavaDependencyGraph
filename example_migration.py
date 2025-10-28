#!/usr/bin/env python3
"""
Example script demonstrating the Java Migration Tool

This script shows how to use the migration engine programmatically
to perform headless code migrations from JIRA tickets.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dependency_graph.migration_engine import MigrationEngine
from dependency_graph.jira_parser import parse_jira_ticket


def main():
    """Example migration workflow"""
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Example JIRA ticket content
    ticket_content = """
    Summary: Refactor UserService to use dependency injection pattern
    
    Description: 
    The current UserService class is tightly coupled to concrete implementations and needs to be refactored to use dependency injection for better testability and maintainability.
    
    Current issues:
    - UserService directly instantiates UserRepository and EmailService
    - Hard to unit test due to tight coupling
    - Violates SOLID principles
    
    Requirements:
    - Replace direct instantiation with constructor injection
    - Create interfaces for UserRepository and EmailService
    - Update all calling code to use the new pattern
    - Maintain backward compatibility during transition
    - Add comprehensive unit tests
    
    Affected classes:
    - UserService
    - UserRepository
    - EmailService
    
    Affected methods:
    - UserService constructor
    - UserService.createUser()
    - UserService.updateUser()
    - UserService.deleteUser()
    
    Priority: High
    Type: refactor
    """
    
    # Example Java project path (you would replace this with your actual project)
    java_project_path = "example_java_project"
    
    # Create example Java project if it doesn't exist
    create_example_project(java_project_path)
    
    print("🚀 Starting Java Migration Tool Example")
    print("=" * 50)
    
    try:
        # Initialize migration engine
        print("1. Initializing migration engine...")
        engine = MigrationEngine()
        print("✅ Migration engine initialized")
        
        # Preview the migration
        print("\n2. Previewing migration...")
        preview = engine.preview_migration(ticket_content, java_project_path)
        
        if "error" in preview:
            print(f"❌ Preview failed: {preview['error']}")
            return
        
        print("✅ Migration preview completed")
        print(f"   • Migration type: {preview['migration_plan']['migration_type']}")
        print(f"   • Affected files: {len(preview['migration_plan']['affected_files'])}")
        print(f"   • Transformation steps: {len(preview['migration_plan']['transformation_steps'])}")
        
        # Execute the migration
        print("\n3. Executing migration...")
        result = engine.migrate_from_jira_ticket(
            ticket_content, 
            java_project_path, 
            "migration_output"
        )
        
        if result.success:
            print("✅ Migration completed successfully!")
            print(f"   • Files processed: {len(result.original_files)}")
            print(f"   • Migration type: {result.migration_plan.migration_type}")
            print(f"   • Validation score: {get_average_validation_score(result)}")
        else:
            print("❌ Migration failed")
            for error in result.errors:
                print(f"   • Error: {error}")
        
        print(f"\n📁 Results saved to: migration_output/")
        print("   • original/ - Original Java files")
        print("   • migrated/ - Migrated Java files")
        print("   • migration_metadata.json - Complete migration report")
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


def create_example_project(project_path: str):
    """Create a simple example Java project for demonstration"""
    project_dir = Path(project_path)
    project_dir.mkdir(exist_ok=True)
    
    # Create example UserService.java
    user_service_code = '''package com.example.service;

import com.example.repository.UserRepository;
import com.example.email.EmailService;

public class UserService {
    private UserRepository userRepository;
    private EmailService emailService;
    
    public UserService() {
        this.userRepository = new UserRepository();
        this.emailService = new EmailService();
    }
    
    public User createUser(String name, String email) {
        User user = new User(name, email);
        userRepository.save(user);
        emailService.sendWelcomeEmail(user.getEmail());
        return user;
    }
    
    public User updateUser(Long id, String name, String email) {
        User user = userRepository.findById(id);
        if (user != null) {
            user.setName(name);
            user.setEmail(email);
            userRepository.save(user);
            emailService.sendUpdateEmail(user.getEmail());
        }
        return user;
    }
    
    public void deleteUser(Long id) {
        User user = userRepository.findById(id);
        if (user != null) {
            userRepository.delete(user);
            emailService.sendGoodbyeEmail(user.getEmail());
        }
    }
}'''
    
    (project_dir / "UserService.java").write_text(user_service_code)
    
    # Create example User.java
    user_code = '''package com.example.service;

public class User {
    private Long id;
    private String name;
    private String email;
    
    public User(String name, String email) {
        this.name = name;
        this.email = email;
    }
    
    // Getters and setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}'''
    
    (project_dir / "User.java").write_text(user_code)
    
    print(f"📁 Created example Java project at: {project_path}")


def get_average_validation_score(result) -> float:
    """Calculate average validation score from migration result"""
    if not result.validation_results:
        return 0.0
    
    scores = []
    for validation in result.validation_results.values():
        score = validation.get('overall_score', 0)
        if score > 0:
            scores.append(score)
    
    return sum(scores) / len(scores) if scores else 0.0


if __name__ == "__main__":
    main()
