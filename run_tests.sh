#!/bin/bash
# Helper script to run tests with proper Python path
# This script ensures all tests can find the dependency_graph module

echo "========================================"
echo "Java Dependency Graph - Test Suite"
echo "========================================"
echo ""

echo "[1/3] Running Quick DOT Generation Test..."
python3 test_kg_fix.py
if [ $? -ne 0 ]; then
    echo "ERROR: Quick DOT test failed!"
    exit 1
fi
echo ""

echo "[2/3] Running Full Dependency Graph Analysis..."
python3 src/tests/test_parser.py example_java_project
if [ $? -ne 0 ]; then
    echo "ERROR: Dependency graph analysis failed!"
    exit 1
fi
echo ""

echo "[3/3] Running Knowledge Graph Generation..."
if [ -z "$TOGETHER_API_KEY" ]; then
    echo "WARNING: TOGETHER_API_KEY not set - skipping knowledge graph test"
    echo "Set API key with: export TOGETHER_API_KEY=your-key"
else
    cd src
    python3 -m dependency_graph.knowledge_graph_generator --project-path ../example_java_project --output-dir ../tmp/knowledge_graph_test
    cd ..
fi

echo ""
echo "========================================"
echo "All tests complete!"
echo "Output files in tmp/ directory"
echo "========================================"
