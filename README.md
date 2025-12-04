# Java Dependency Graph

A Python tool for analyzing Java code dependencies and generating dependency graphs using Tree-sitter parsing and Graphviz visualization.

## Quick Start

### Option 1: Quick Testing (Phase 1 - No Installation)
```bash
# Clone the repository
git clone <your-repo-url>
cd JavaDependencyGraph

# Install dependencies
pip install -r requirements.txt

# Install Graphviz (Windows)
winget install graphviz

# Run tests using helper script
run_tests.bat       # Windows
./run_tests.sh      # Linux/Mac
```

### Option 2: Proper Installation (Phase 2 - Recommended)
```bash
# Clone the repository
git clone <your-repo-url>
cd JavaDependencyGraph

# Set up virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install package in development mode
pip install -e .

# Install Graphviz
winget install graphviz  # Windows
brew install graphviz    # macOS
sudo apt-get install graphviz  # Linux

# Set API key (for LLM features)
export TOGETHER_API_KEY="your-key"  # Linux/Mac
set TOGETHER_API_KEY=your-key       # Windows

# Run analysis using console scripts
java-dep-analyze example_java_project
java-knowledge-graph --project-path example_java_project --output-dir tmp/kg
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

### Method 1: Quick Setup (No Package Installation)

For quick testing without installing the package:

```bash
# Install dependencies
pip install -r requirements.txt

# Install Graphviz
winget install graphviz  # Windows
brew install graphviz    # macOS
sudo apt-get install graphviz  # Linux

# Use helper scripts to run tests
run_tests.bat  # Windows
./run_tests.sh  # Linux/Mac
```

### Method 2: Full Installation (Recommended)

For development or regular use, install as an editable package:

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install package in development mode
pip install -e .

# Install Graphviz
winget install graphviz  # Windows
brew install graphviz    # macOS
sudo apt-get install graphviz  # Linux

# Verify installation
java-knowledge-graph --help
java-dep-analyze --help
```

**Note**: After installing Graphviz on Windows, make sure to add it to your PATH or restart your terminal.

### API Key Setup

For LLM-powered features (knowledge graph generation, migration):

```bash
# Set environment variable
export TOGETHER_API_KEY="your-together-ai-key"  # Linux/Mac
set TOGETHER_API_KEY=your-together-ai-key       # Windows

# OR create .env file in project root
echo "TOGETHER_API_KEY=your-key" > .env
```

## Usage

### Using Console Scripts (After `pip install -e .`)

```bash
# Analyze Java project dependencies
java-dep-analyze path/to/java/project

# Generate LLM-powered knowledge graph
java-knowledge-graph --project-path example_java_project --output-dir tmp/kg

# Run migration from JIRA ticket
java-dep-migrate --ticket-file ticket.txt --project path/to/project
```

### Using Python Commands Directly

```bash
# Dependency analysis
python src/tests/test_parser.py path/to/java/project

# Knowledge graph (Windows - note the -X utf8 flag!)
cd src
python -X utf8 -m dependency_graph.knowledge_graph_generator \
  --project-path ../example_java_project \
  --output-dir ../tmp/knowledge_graph
cd ..
```

This will:
1. Parse all `.java` files in the project
2. Analyze dependencies between classes and methods
3. Generate dependency graphs in `tmp/graph_out/`
4. Export structured data as JSON/JSONL files

### LLM-Powered Knowledge Graph

The repository includes `src/dependency_graph/knowledge_graph_generator.py`, which:

1. Parses a Java project with Tree-sitter
2. Calls an LLM (Together.ai) to summarize every method
3. Requests the LLM to transform those summaries into a Graphviz DOT graph
4. Renders PNG/SVG knowledge graph artifacts

**Prerequisites**

- Set `TOGETHER_API_KEY` in your environment or pass `--api-key`
- Ensure Graphviz is installed and available on your `PATH`

**Run the generator (using console script after `pip install -e .`)**:

```bash
java-knowledge-graph \
  --project-path example_java_project \
  --output-dir tmp/knowledge_graph
```

**Run using Python directly** (if not installed as package):

```bash
# Windows
cd src
python -X utf8 -m dependency_graph.knowledge_graph_generator ^
  --project-path ../example_java_project ^
  --output-dir ../tmp/knowledge_graph
cd ..

# Linux/Mac
cd src
python3 -m dependency_graph.knowledge_graph_generator \
  --project-path ../example_java_project \
  --output-dir ../tmp/knowledge_graph
cd ..
```

**Outputs:**

- `tmp/knowledge_graph/function_descriptions.json`
- `tmp/knowledge_graph/knowledge_graph.dot`
- `tmp/knowledge_graph/knowledge_graph.png`
- `tmp/knowledge_graph/knowledge_graph.svg`

**Mandate-Focused Subgraph:**

Generate focused knowledge graphs for specific tasks:

```bash
# Using console script
java-knowledge-graph \
  --project-path example_java_project \
  --output-dir tmp/mandate_graph \
  --mandate "user management and authentication" \
  --dependency-graph-dir tmp/graph_out
```

---

### Testing on Your Own Java Projects

#### Step 1: Run Basic Analysis

```bash
# Analyze your repository
python src/tests/test_parser.py path/to/your/java/project

# Check outputs
ls tmp/graph_out/
# Files: dep.png, dep.svg, nodes.jsonl, edges.jsonl, symbol_tables.json
```

#### Step 2: Generate Mandate-Focused Knowledge Graph

```bash
# Set API key
set TOGETHER_API_KEY=your-key  # Windows
export TOGETHER_API_KEY=your-key  # Linux/Mac

# Generate focused analysis
cd src
python -X utf8 -m dependency_graph.knowledge_graph_generator ^
  --project-path path/to/your/java/project ^
  --output-dir ../tmp/my_analysis ^
  --mandate "describe your focus area here" ^
  --dependency-graph-dir ../tmp/graph_out
cd ..
```

**Example Mandate Queries:**
- "authentication and user login functionality"
- "payment processing and transaction handling"
- "database operations and data persistence"
- "API endpoints and REST controllers"
- "security and authorization logic"
- "file upload and storage handling"

#### Step 3: View Results

```bash
# Windows
start tmp/my_analysis/knowledge_graph.png
start tmp/my_analysis/subgraph/subgraph.png

# Linux/Mac
open tmp/my_analysis/knowledge_graph.png
open tmp/my_analysis/subgraph/subgraph.png
```

**Output Structure:**
```
tmp/my_analysis/
├── function_descriptions.json     # LLM-generated method summaries
├── knowledge_graph.dot            # Full knowledge graph (DOT format)
├── knowledge_graph.png            # Full knowledge graph visualization
├── knowledge_graph.svg            # Full knowledge graph (scalable)
└── subgraph/
    ├── nodes.jsonl                # Filtered nodes relevant to mandate
    ├── edges.jsonl                # Filtered edges
    ├── subgraph.dot               # Subgraph (DOT format)
    ├── subgraph.png               # Focused subgraph visualization
    └── subgraph.svg               # Focused subgraph (scalable)
```

---

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
