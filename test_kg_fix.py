"""
Quick test script to verify knowledge graph DOT generation fix.
Run this to test if the empty DOT file issue is resolved.
"""

import sys
import os
# Add src/ to Python path so imports work (Phase 1 - without pip install)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pathlib import Path
from dependency_graph.llm_integration import LLMIntegration, FunctionDescription

# Test DOT generation with minimal data
def test_dot_generation():
    print("Testing DOT generation fix...")

    # Create minimal function descriptions
    test_descriptions = [
        FunctionDescription(
            name="testMethod",
            class_name="TestClass",
            package="com.example",
            signature="public void testMethod()",
            description="A test method",
            parameters=[],
            return_type="void",
            return_description="Returns nothing",
            complexity="Simple",
            dependencies=[],
            side_effects=[],
            usage_context="Testing"
        )
    ]

    # Initialize LLM (requires API key)
    try:
        llm = LLMIntegration()
        dot_source = llm.generate_knowledge_graph_dot(
            test_descriptions,
            title="Test Graph"
        )

        print(f"✅ Generated DOT source ({len(dot_source)} bytes)")
        print(f"First 200 chars: {dot_source[:200]}")

        # Verify it contains expected content
        if "digraph" in dot_source or "graph" in dot_source:
            print("✅ DOT source looks valid!")
            return True
        else:
            print("❌ DOT source doesn't look like valid Graphviz")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_dot_generation()
