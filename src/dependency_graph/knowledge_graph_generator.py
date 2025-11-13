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
        default=os.getenv("OPENAI_API_KEY"),
        help=(
            "Optional OpenAI API key (defaults to OPENAI_API_KEY "
            "environment variable)."
        ),
    )

    args = parser.parse_args()
    if not args.api_key:
        parser.error(
            "OpenAI API key must be provided via --api-key or "
            "OPENAI_API_KEY environment variable."
        )

    generate_knowledge_graph(
        project_path=args.project_path,
        output_dir=args.output_dir,
        model=args.model,
        api_key=args.api_key,
        title=args.title,
    )


if __name__ == "__main__":
    main()
