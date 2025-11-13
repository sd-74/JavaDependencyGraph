# Java Dependency Graph

A Python tool for analyzing Java code dependencies and generating dependency graphs using Tree-sitter parsing and Graphviz visualization.

## Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd JavaDependencyGraph

# Set up virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install Graphviz (Windows)
winget install graphviz
# OR download from https://graphviz.org/download/

# Run analysis
python src/tests/test_parser.py path/to/java/project
```

## Features

- **Java Code Parsing**: Uses Tree-sitter to parse Java source files and extract symbols
- **Dependency Analysis**: Analyzes method calls, object instantiation, inheritance, and method overrides
- **Graph Visualization**: Generates PNG and SVG dependency graphs using Graphviz
- **LLM-Assisted Knowledge Graph**: Describes Java methods with an LLM and renders a knowledge graph via Graphviz
- **Structured Output**: Exports dependency data as JSON/JSONL for further analysis

## Project Structure

```
java-dependency-graph/
├── src/
│   ├── dependency_graph/
│   │   ├── __init__.py
│   │   ├── java_parser.py          # Tree-sitter Java parsing
│   │   ├── analyzer.py             # Repository indexing
│   │   ├── dependency_analyzer.py  # Core dependency analysis logic
│   │   └── dot_exporter.py         # Graphviz output generation
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py           # File discovery utilities
├── tests/
│   └── test_parser.py              # CLI test runner
├── build/                          # Tree-sitter language builds
├── tmp/graph_out/                  # Output directory
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.8+
- Git (for cloning tree-sitter-java)
- Graphviz (for graph generation)

## Installation

### Python Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Graphviz

- **Windows**: `winget install graphviz` or download from [Graphviz website](https://graphviz.org/download/)
- **macOS**: `brew install graphviz`
- **Linux**: `sudo apt-get install graphviz` (Ubuntu/Debian)

**Note**: After installing Graphviz on Windows, make sure to add it to your PATH or restart your terminal.

## Usage

Run the dependency analysis on a Java project:

```bash
python src/tests/test_parser.py path/to/java/project
```

This will:
1. Parse all `.java` files in the project
2. Analyze dependencies between classes and methods
3. Generate dependency graphs in `tmp/graph_out/`
4. Export structured data as JSON/JSONL files

### LLM-Powered Knowledge Graph

The repository includes `src/dependency_graph/knowledge_graph_generator.py`, which:

1. Parses a Java project with Tree-sitter
2. Calls an LLM to summarize every method
3. Requests the LLM to transform those summaries into a Graphviz DOT graph
4. Renders PNG/SVG knowledge graph artifacts

**Prerequisites**

- Set `OPENAI_API_KEY` in your environment or pass `--api-key`
- Ensure Graphviz is installed and available on your `PATH`

**Run the generator for the bundled example project**:

```bash
python -m dependency_graph.knowledge_graph_generator \
  --project-path example_java_project \
  --output-dir tmp/knowledge_graph \
  --model gpt-4o-mini
```

Outputs:

- `tmp/knowledge_graph/function_descriptions.json`
- `tmp/knowledge_graph/knowledge_graph.dot`
- `tmp/knowledge_graph/knowledge_graph.png`
- `tmp/knowledge_graph/knowledge_graph.svg`

## Output Files

The tool generates several output files in `tmp/graph_out/`:

- `dep.png` / `dep.svg` - Visual dependency graphs
- `nodes.jsonl` - All nodes in the dependency graph
- `edges.jsonl` - All edges/relationships between nodes
- `symbol_tables.json` - Raw parsed symbol information

## Dependency Analysis

The tool analyzes several types of dependencies:

- **ParentOf/ChildOf**: Module → Class → Method hierarchy
- **BaseClassOf/DerivedClassOf**: Inheritance relationships
- **Overrides/OverriddenBy**: Method overriding relationships
- **Calls/CalledBy**: Method invocation relationships
- **Instantiates/InstantiatedBy**: Object creation relationships

## Node ID Schema

Nodes use a canonical ID format:

- `class:<fqn>` - Java classes
- `method:<owner_fqn>#<name>(<sig>)` - Methods
- `constructor:<owner_fqn>::<init>(<sig>)` - Constructors
- `field:<owner_fqn>#<name>` - Fields
- `module:<pkg_or_default>` - Packages/modules

## Edge Schema

All edges follow a unified schema:
```json
{
  "src": "<node_id>",
  "label": "<EdgeType>",
  "dst": "<node_id>",
  "resolved": true
}
```

## Example Output

Expected edge counts for a typical Java project:
```json
{
  "ParentOf": 6, "ChildOf": 6,
  "BaseClassOf": 1, "DerivedClassOf": 1,
  "Overrides": 1, "OverriddenBy": 1,
  "Instantiates": 1, "InstantiatedBy": 1,
  "Calls": 2, "CalledBy": 2
}
```

## Troubleshooting

1. **Empty statements**: Check that Tree-sitter is capturing `method_invocation` and `object_creation_expression` nodes
2. **Missing dependencies**: Verify that local variable declarations are being parsed correctly
3. **Graphviz errors**: Ensure Graphviz is installed and accessible in PATH

## Dependencies

- `tree_sitter==0.21.3` - Java code parsing
- `graphviz==0.20.3` - Graph visualization
