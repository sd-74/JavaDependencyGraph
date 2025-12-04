# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Python-based Java static analysis and migration tool that:
1. Parses Java source code using Tree-sitter
2. Extracts dependency graphs (classes, methods, inheritance, calls)
3. Generates visual graph representations using Graphviz
4. Uses LLM integration (OpenAI/Anthropic) for automated code migrations from JIRA tickets
5. Provides subgraph extraction and mandate-based filtering for focused analysis

## Environment Setup

```bash
# Activate virtual environment (REQUIRED before any Python commands)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies (if needed)
pip install -r requirements.txt

# Install Graphviz (Windows)
winget install graphviz
```

## Common Commands

### Quick Start (Easiest)
```bash
# Windows
run_tests.bat

# Linux/Mac
chmod +x run_tests.sh
./run_tests.sh
```

### Basic Dependency Analysis (No API Key Required)
```bash
# Analyze a Java project
python src/tests/test_parser.py path/to/java/project

# Output goes to tmp/graph_out/:
# - dep.png/dep.svg (visual graphs)
# - nodes.jsonl (all nodes)
# - edges.jsonl (all relationships)
# - symbol_tables.json (raw parsed data)
```

### LLM-Powered Knowledge Graph (Requires Together.ai API Key)
```bash
# Set API key first
export TOGETHER_API_KEY="your-key"  # Linux/Mac
set TOGETHER_API_KEY=your-key       # Windows

# Generate knowledge graph (Windows - note the -X utf8 flag!)
cd src
python -X utf8 -m dependency_graph.knowledge_graph_generator ^
  --project-path ../example_java_project ^
  --output-dir ../tmp/knowledge_graph
cd ..

# Generate knowledge graph (Linux/Mac)
cd src
python3 -m dependency_graph.knowledge_graph_generator \
  --project-path ../example_java_project \
  --output-dir ../tmp/knowledge_graph
cd ..
```

### Mandate-Focused Subgraph Analysis
```bash
# 1. Generate base dependency graph first
python src/tests/test_parser.py example_java_project

# 2. Run mandate-focused analysis (Windows)
cd src
python -X utf8 -m dependency_graph.knowledge_graph_generator ^
  --project-path ../example_java_project ^
  --output-dir ../tmp/mandate_graph ^
  --mandate "user management and data handling" ^
  --dependency-graph-dir ../tmp/graph_out
cd ..

# 2. Run mandate-focused analysis (Linux/Mac)
cd src
python3 -m dependency_graph.knowledge_graph_generator \
  --project-path ../example_java_project \
  --output-dir ../tmp/mandate_graph \
  --mandate "user management and data handling" \
  --dependency-graph-dir ../tmp/graph_out
cd ..
```

### Full Migration Tool (Requires Together.ai API Key)
```bash
# Preview migration plan without executing
python src/migration_cli.py \
  --ticket-file sample_ticket.txt \
  --project path/to/java/project \
  --preview

# Execute full migration
python src/migration_cli.py \
  --ticket-file sample_ticket.txt \
  --project path/to/java/project \
  --output migration_results
```

## Important Notes

### Windows Users
Always use `python -X utf8` flag when running knowledge graph generators to avoid emoji encoding errors in console output.

### Module Import Issues
If you encounter `ModuleNotFoundError: No module named 'dependency_graph'`:
- Run commands from the **project root** directory
- Use the provided helper scripts (`run_tests.bat` or `run_tests.sh`)
- For manual testing, ensure you're using the correct working directory as shown in examples above

## Architecture

### Core Analysis Pipeline (5 Stages)

The dependency analyzer (`src/dependency_graph/dependency_analyzer.py`) processes Java code through 5 stages:

1. **Stage 1 (Syntactic)**: Creates module/class/interface/method nodes, establishes ParentOf/ChildOf hierarchy
2. **Stage 2 (Symbol Building)**: Indexes classes, methods, and constructors by FQN and signature
3. **Stage 3a (CHA)**: Resolves inheritance (BaseClassOf/DerivedClassOf) and method overrides (Overrides/OverriddenBy)
4. **Stage 3b (Implements)**: Links interface implementations and interface methods
5. **Stage 4 (Calls/News)**: Analyzes method calls and object instantiation (Calls/CalledBy, Instantiates/InstantiatedBy)
6. **Stage 5 (Type Usage)**: Tracks field and parameter type usage

All stages must be run sequentially. Each stage depends on data structures built by previous stages.

### Node ID Schema

All nodes use canonical IDs:
- `module:<package_name>` - Java packages
- `class:<fqn>` - Java classes
- `interface:<fqn>` - Java interfaces
- `method:<owner_fqn>#<name>(<signature>)` - Methods
- `constructor:<owner_fqn>::<init>(<signature>)` - Constructors
- `field:<owner_fqn>#<name>` - Fields

### Edge Types

All edges follow the schema `{src, label, dst, resolved}`:
- **ParentOf/ChildOf**: Module→Class→Method hierarchy
- **BaseClassOf/DerivedClassOf**: Inheritance
- **Implements/ImplementedBy**: Interface implementation
- **Overrides/OverriddenBy**: Method overriding
- **Calls/CalledBy**: Method invocations
- **Instantiates/InstantiatedBy**: Object creation
- **Uses/UsedBy**: Type usage (fields, parameters)

### Migration Engine Flow

The migration engine (`src/dependency_graph/migration_engine.py`) orchestrates:

1. **JIRA Parsing** (`jira_parser.py`): Extract MigrationRequirement from ticket
2. **AST Analysis** (`analyzer.py` → `dependency_analyzer.py`): Full dependency graph
3. **LLM Function Analysis** (`llm_integration.py`): Extract FunctionDescription for each method
4. **Migration Planning**: LLM generates MigrationPlan with transformation steps
5. **Execution**: Apply transformations to files
6. **Validation**: Validate migrated code

### Subgraph Extraction

`subgraph_extractor.py` provides focused analysis:
- Takes seed nodes (mandate-relevant classes/methods)
- BFS traversal with configurable depth
- Filters by edge types (Calls, Uses, Instantiates, inheritance)
- Returns minimal subgraph for targeted analysis/migration

### Mandate Filtering

`mandate_filter.py` uses LLM to determine file relevance:
- Accepts mandate/task description
- Analyzes each file's source code
- Returns boolean relevance decision
- Caches results to avoid redundant API calls
- Supports both OpenAI and Anthropic models

## Key Design Patterns

### Tree-sitter Parsing
- Java grammar is in `build/tree-sitter-java/`
- Parser automatically clones and builds on first run
- Language binary cached in `build/languages.so`
- All parsing uses byte ranges, converted to line numbers for output

### Metadata Enrichment
All nodes contain metadata:
- `file_path`: Relative path to source file
- `line_range`: [start_line, end_line]
- `source_code`: Extracted code snippet
- `owner_fqn`: Fully qualified name of containing class
- Methods include: `return_type`, `params`, `is_static`, `is_constructor`

### LLM Integration
- Supports OpenAI (default) and Anthropic Claude
- Model configurable via CLI (`--model gpt-4o-mini`)
- API key from environment: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- Three main operations:
  1. `analyze_function_descriptions()`: Summarize methods
  2. `generate_knowledge_graph()`: Create DOT graph from descriptions
  3. `generate_migration_plan()`: Plan code transformations

## Important Notes

### Running Tests
The "test" file `src/tests/test_parser.py` is actually the main CLI entry point for basic analysis. It's not a unit test - it's the primary command for generating dependency graphs.

### Tree-sitter Deprecation Warnings
The tool uses `tree_sitter==0.21.3`, which shows deprecation warnings. These are expected and don't affect functionality. The codebase hasn't migrated to the newer Tree-sitter Python API yet.

### Graphviz Dependency
All graph visualization requires Graphviz installed and in PATH. The tool will fail silently or with cryptic errors if Graphviz is missing.

### Byte vs Line Positions
Parser works in byte offsets. Helper function `byte_to_line()` converts to 1-indexed line numbers. Always use line numbers in output/metadata, byte ranges for slicing source.

### Symbol Resolution Strategy
- Stage 2 builds lookup tables: `classes_by_fqn`, `methods_by_owner_sig`
- Stage 3 uses these for inheritance and override resolution
- Stage 4 uses local context (enclosing class) for call resolution
- Unresolved calls are still added to edges with `resolved: false`

### Interface vs Class Handling
- Interfaces and classes are distinct node types (`interface:*` vs `class:*`)
- Interfaces use `extends` field (for interface inheritance)
- Classes use `extends` (for superclass) and `implements` (for interfaces)
- Stage 3b specifically handles interface implementation relationships
