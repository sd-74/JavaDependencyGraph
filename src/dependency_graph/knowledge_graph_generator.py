import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import List

from graphviz import Source

from dependency_graph.java_parser import parse_file
from dependency_graph.llm_integration import (
    LLMIntegration,
    FunctionDescription,
)
from dependency_graph.mandate_filter import MandateFilter
from dependency_graph.subgraph_extractor import SubgraphExtractor
from utils.file_utils import find_files


def _extract_function_descriptions(
    project_path: Path, llm: LLMIntegration
) -> List[FunctionDescription]:
    descriptions: List[FunctionDescription] = []

    java_files = find_files(project_path, (".java",))
    if not java_files:
        raise FileNotFoundError(f"No Java files found under {project_path}")

    for java_file in java_files:
        parsed = parse_file(java_file)
        package = parsed["symbols"]["package"]
        src_bytes = Path(java_file).read_bytes()

        for type_info in parsed["symbols"]["types"]:
            start, end = type_info["range"]
            class_code = src_bytes[start:end].decode("utf-8")
            class_name = type_info["name"]

            class_descriptions = llm.analyze_function_descriptions(
                java_code=class_code,
                class_name=class_name,
                package=package,
            )

            descriptions.extend(class_descriptions)

    return descriptions


def _render_graph(
    dot_source: str, output_dir: Path, base_name: str = "knowledge_graph"
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    dot_path = output_dir / f"{base_name}.dot"
    dot_path.write_text(dot_source, encoding="utf-8")

    graph = Source(dot_source)
    graph.format = "png"
    graph.render(filename=str(output_dir / base_name), cleanup=True)

    graph.format = "svg"
    graph.render(filename=str(output_dir / base_name), cleanup=True)


def generate_knowledge_graph(
    project_path: Path,
    output_dir: Path,
    model: str,
    api_key: str | None,
    title: str,
) -> None:
    llm = LLMIntegration(api_key=api_key, model=model)

    function_descriptions = _extract_function_descriptions(project_path, llm)

    if not function_descriptions:
        raise RuntimeError(
            "No function descriptions were generated from the project."
        )

    # Persist raw function descriptions for transparency/debugging
    descriptions_path = output_dir / "function_descriptions.json"
    descriptions_path.parent.mkdir(parents=True, exist_ok=True)
    descriptions_path.write_text(
        json.dumps(
            [asdict(desc) for desc in function_descriptions],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    dot_source = llm.generate_knowledge_graph_dot(
        function_descriptions, title=title
    )
    _render_graph(dot_source, output_dir)

    print(f"Knowledge graph generated at {output_dir}")


def generate_mandate_focused_knowledge_graph(
    project_path: Path,
    output_dir: Path,
    mandate: str,
    dependency_graph_dir: Path,  # Path to edges.jsonl and nodes.jsonl
    model: str,
    api_key: str,
    title: str,
) -> None:
    """
    Generate knowledge graph focused on mandate-relevant code.

    Workflow:
    1. Load full dependency graph
    2. Use LLM to filter files by mandate relevance
    3. Extract focused subgraph for relevant files
    4. Generate LLM descriptions only for subgraph nodes
    5. Create knowledge graph from enriched subgraph
    """
    print(f"🎯 Mandate: {mandate}")

    # Step 1: Load dependency graph
    print("\n📂 Loading dependency graph...")
    nodes_path = dependency_graph_dir / "nodes.jsonl"
    edges_path = dependency_graph_dir / "edges.jsonl"

    if not nodes_path.exists() or not edges_path.exists():
        raise FileNotFoundError(
            f"Dependency graph files not found in {dependency_graph_dir}. "
            "Please run test_parser.py first to generate nodes.jsonl and edges.jsonl"
        )

    nodes = [json.loads(line) for line in nodes_path.read_text().splitlines() if line.strip()]
    edges = [json.loads(line) for line in edges_path.read_text().splitlines() if line.strip()]
    print(f"   Loaded {len(nodes)} nodes, {len(edges)} edges")

    # Step 2: Load source files for mandate filtering
    print("\n📄 Loading source files...")
    source_files = {}
    java_files = find_files(project_path, (".java",))
    for java_file in java_files:
        rel_path = str(Path(java_file).relative_to(project_path))
        source_files[rel_path] = Path(java_file).read_text(encoding="utf-8")

    # Step 3: Filter nodes by mandate relevance
    mandate_filter = MandateFilter(api_key=api_key, model=model, use_openai=("gpt" in model.lower() or "openai" in model.lower()))
    relevant_node_ids = mandate_filter.filter_nodes_by_mandate(
        nodes, source_files, mandate
    )

    if not relevant_node_ids:
        raise RuntimeError(f"No files were relevant to mandate: '{mandate}'")

    # Step 4: Extract focused subgraph
    print("\n🔗 Extracting focused subgraph...")
    extractor = SubgraphExtractor(nodes, edges)
    subgraph_nodes, subgraph_edges = extractor.extract_focused_subgraph(
        seed_node_ids=relevant_node_ids,
        include_dependencies=True,
        include_dependents=True,
        max_depth=2
    )

    # Step 5: Export subgraph for reference
    subgraph_dir = output_dir / "subgraph"
    subgraph_dir.mkdir(parents=True, exist_ok=True)
    (subgraph_dir / "nodes.jsonl").write_text(
        "\n".join(json.dumps(n) for n in subgraph_nodes)
    )
    (subgraph_dir / "edges.jsonl").write_text(
        "\n".join(json.dumps(e) for e in subgraph_edges)
    )

    # Step 6: Generate LLM descriptions for subgraph methods
    print("\n🤖 Generating LLM descriptions for focused subgraph...")
    llm = LLMIntegration(api_key=api_key, model=model)

    function_descriptions = []
    method_nodes = [n for n in subgraph_nodes if n["id"].startswith("method:")]

    for method_node in method_nodes:
        metadata = method_node.get("metadata", {})
        source_code = metadata.get("source_code", "")

        if not source_code:
            continue

        # Extract class and package info
        owner_fqn = metadata.get("owner_fqn", "")
        parts = owner_fqn.rsplit(".", 1)
        package = parts[0] if len(parts) > 1 else ""
        class_name = parts[1] if len(parts) > 1 else owner_fqn

        # Generate description for this method
        descriptions = llm.analyze_function_descriptions(
            java_code=source_code,
            class_name=class_name,
            package=package,
        )
        function_descriptions.extend(descriptions)

    if not function_descriptions:
        raise RuntimeError("No function descriptions were generated from subgraph.")

    # Step 7: Save descriptions
    descriptions_path = output_dir / "function_descriptions.json"
    descriptions_path.write_text(
        json.dumps(
            [asdict(desc) for desc in function_descriptions],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Step 8: Generate knowledge graph visualization
    print("\n📊 Generating knowledge graph...")
    dot_source = llm.generate_knowledge_graph_dot(
        function_descriptions, title=f"{title}\nMandate: {mandate}"
    )
    _render_graph(dot_source, output_dir)

    print(f"\n✅ Mandate-focused knowledge graph generated at {output_dir}")
    print(f"   - Analyzed {len(method_nodes)} methods from {len(relevant_node_ids)} relevant nodes")
    print(f"   - Generated {len(function_descriptions)} function descriptions")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a knowledge graph for a Java project using "
            "LLM-assisted analysis."
        )
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "example_java_project",
        help=(
            "Path to the Java project to analyze (default: example project in "
            "the repo)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2] / "tmp" / "knowledge_graph"
        ),
        help=(
            "Directory to write the graph artifacts "
            "(default: tmp/knowledge_graph)."
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4",
        help="LLM model identifier to use for OpenAI API calls.",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="Java Project Knowledge Graph",
        help="Title to embed in the Graphviz diagram.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
        help=(
            "Optional API key (defaults to OPENAI_API_KEY or ANTHROPIC_API_KEY "
            "environment variable)."
        ),
    )
    parser.add_argument(
        "--mandate",
        type=str,
        default=None,
        help="Optional mandate/task to filter relevant code (e.g., 'payment processing')"
    )
    parser.add_argument(
        "--dependency-graph-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "tmp" / "graph_out",
        help="Directory containing edges.jsonl and nodes.jsonl from dependency analyzer"
    )

    args = parser.parse_args()
    if not args.api_key:
        parser.error(
            "API key must be provided via --api-key or "
            "OPENAI_API_KEY/ANTHROPIC_API_KEY environment variable."
        )

    if args.mandate:
        # Use mandate-focused workflow
        generate_mandate_focused_knowledge_graph(
            project_path=args.project_path,
            output_dir=args.output_dir,
            mandate=args.mandate,
            dependency_graph_dir=args.dependency_graph_dir,
            model=args.model,
            api_key=args.api_key,
            title=args.title,
        )
    else:
        # Use original full-repo workflow
        generate_knowledge_graph(
            project_path=args.project_path,
            output_dir=args.output_dir,
            model=args.model,
            api_key=args.api_key,
            title=args.title,
        )


if __name__ == "__main__":
    main()
