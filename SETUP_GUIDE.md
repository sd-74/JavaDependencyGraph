# Java Dependency Graph & Migration Tool - Setup Guide

## ✅ Virtual Environment Setup Complete!

Your Java migration tool is now fully set up and ready to use. Here's what we've accomplished:

### 🎯 **What's Working**

1. **✅ Virtual Environment**: Created `.venv` with all dependencies
2. **✅ Core Dependencies**: Tree-sitter, Graphviz, OpenAI, Pydantic, etc.
3. **✅ Java Parsing**: AST analysis and dependency extraction
4. **✅ Graph Visualization**: PNG and SVG dependency graphs
5. **✅ JIRA Parsing**: Extract migration requirements from tickets
6. **✅ Migration Engine**: Complete orchestration framework

### 🚀 **Quick Start**

#### 1. Activate Virtual Environment
```bash
source .venv/bin/activate
```

#### 2. Basic Dependency Analysis (No API Key Required)
```bash
# Analyze any Java project
python src/tests/test_parser.py /path/to/your/java/project

# This generates:
# - tmp/graph_out/dep.png (dependency graph)
# - tmp/graph_out/dep.svg (vector graph)
# - tmp/graph_out/nodes.jsonl (all nodes)
# - tmp/graph_out/edges.jsonl (all relationships)
# - tmp/graph_out/symbol_tables.json (raw data)
```

#### 3. Full Migration Tool (Requires OpenAI API Key)
```bash
# Set your API key
export OPENAI_API_KEY="your-openai-api-key-here"

# Preview migration without executing
python src/migration_cli.py --ticket-file sample_ticket.txt --project /path/to/java/project --preview

# Execute full migration
python src/migration_cli.py --ticket-file sample_ticket.txt --project /path/to/java/project --output migration_results
```

### 📁 **Project Structure**

```
JavaDependencyGraph/
├── .venv/                          # Virtual environment
├── src/
│   ├── dependency_graph/
│   │   ├── java_parser.py          # Java AST parsing
│   │   ├── dependency_analyzer.py  # Dependency analysis
│   │   ├── jira_parser.py          # JIRA ticket parsing
│   │   ├── llm_integration.py      # OpenAI integration
│   │   ├── migration_engine.py     # Main migration logic
│   │   └── dot_exporter.py         # Graph visualization
│   ├── utils/
│   │   └── file_utils.py           # File discovery
│   └── migration_cli.py            # Command-line interface
├── example_java_project/           # Sample Java project
├── sample_ticket.txt               # Example JIRA ticket
├── config_example.env              # Environment config template
└── requirements.txt                # Dependencies
```

### 🔧 **Configuration**

#### Environment Variables
```bash
# Required for LLM features
export OPENAI_API_KEY="your-openai-api-key"

# Optional for JIRA API integration
export JIRA_BASE_URL="https://your-company.atlassian.net"
export JIRA_API_TOKEN="your-jira-token"
```

#### API Key Setup
1. Get your OpenAI API key from: https://platform.openai.com/api-keys
2. Set it as an environment variable:
   ```bash
   export OPENAI_API_KEY="sk-proj-your-key-here"
   ```
3. Or copy `config_example.env` to `.env` and edit it

### 🧪 **Testing the Tool**

#### Test Core Functionality (No API Key)
```bash
# Test basic parsing and analysis
python -c "
import sys; sys.path.append('src')
from dependency_graph.jira_parser import parse_jira_ticket
from dependency_graph.analyzer import index_repo

# Test JIRA parsing
ticket = 'Summary: Refactor UserService\nType: refactor'
req = parse_jira_ticket(ticket)
print(f'✅ JIRA parsing: {req.title}')

# Test file analysis
files = index_repo('example_java_project')
print(f'✅ File analysis: {len(files)} files found')
"
```

#### Test Full Migration (With API Key)
```bash
export OPENAI_API_KEY="your-key"
python src/migration_cli.py --ticket-file sample_ticket.txt --project example_java_project --preview
```

### 📊 **Example Output**

The tool generates comprehensive outputs:

#### Dependency Analysis
- **Visual Graphs**: `dep.png` and `dep.svg` showing class relationships
- **Structured Data**: JSON files with nodes, edges, and symbol tables
- **Edge Types**: ParentOf, ChildOf, Calls, Instantiates, etc.

#### Migration Results
- **Original Files**: `migration_output/original/`
- **Migrated Files**: `migration_output/migrated/`
- **Metadata**: `migration_output/migration_metadata.json`
- **Validation**: Detailed validation results and scores

### 🎯 **Key Features**

1. **JIRA Integration**: Parse tickets to extract migration requirements
2. **AST Analysis**: Deep understanding of Java code structure
3. **LLM-Powered**: Intelligent code generation and analysis
4. **Dependency Mapping**: Complete dependency graph visualization
5. **Migration Planning**: Step-by-step transformation plans
6. **Validation**: Automated code validation and testing
7. **Preview Mode**: See migration plans before execution

### 🚨 **Troubleshooting**

#### Common Issues

1. **API Key Quota**: If you get quota errors, check your OpenAI billing
2. **Graphviz Missing**: Install with `brew install graphviz` (macOS)
3. **Tree-sitter Warnings**: These are deprecation warnings, not errors
4. **Import Errors**: Make sure you're in the virtual environment

#### Getting Help

- Check the generated files in `tmp/graph_out/` for analysis results
- Use `--preview` mode to see migration plans without executing
- Check `migration_output/migration_metadata.json` for detailed results

### 🎉 **You're Ready!**

Your Java migration tool is fully functional and ready to use. The core dependency analysis works without any API keys, and the full migration capabilities are available with a valid OpenAI API key.

Start with basic dependency analysis on your Java projects, then move to full migrations once you have your API key set up!
