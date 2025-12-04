@echo off
REM Helper script to run tests with proper Python path
REM This script ensures all tests can find the dependency_graph module

echo ========================================
echo Java Dependency Graph - Test Suite
echo ========================================
echo.

echo [1/3] Running Quick DOT Generation Test...
python -X utf8 test_kg_fix.py
if errorlevel 1 (
    echo ERROR: Quick DOT test failed!
    pause
    exit /b 1
)
echo.

echo [2/3] Running Full Dependency Graph Analysis...
python -X utf8 src\tests\test_parser.py example_java_project
if errorlevel 1 (
    echo ERROR: Dependency graph analysis failed!
    pause
    exit /b 1
)
echo.

echo [3/3] Running Knowledge Graph Generation...
if not defined TOGETHER_API_KEY (
    echo WARNING: TOGETHER_API_KEY not set - skipping knowledge graph test
    echo Set API key with: set TOGETHER_API_KEY=your-key
    goto :skip_kg
)

cd src
python -X utf8 -m dependency_graph.knowledge_graph_generator --project-path ..\example_java_project --output-dir ..\tmp\knowledge_graph_test
cd ..

:skip_kg
echo.
echo ========================================
echo All tests complete!
echo Output files in tmp\ directory
echo ========================================
pause
