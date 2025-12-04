import json
import sys
import os
from pathlib import Path

# Add parent directory to path for Phase 1 compatibility (works with or without pip install -e .)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dependency_graph.analyzer import index_repo
from dependency_graph.dependency_analyzer import Analyzer
from dependency_graph.dot_exporter import to_dot

def main():
    repo = Path(sys.argv[1])
    out = Path("tmp/graph_out")
    out.mkdir(parents=True, exist_ok=True)

    files = index_repo(repo)
    # write symbol tables for inspection
    (out / "symbol_tables.json").write_text(
        json.dumps(files, indent=2, ensure_ascii=False)
    )

    an = Analyzer()
    an.files = files
    an.stage1_add_syntactic()
    an.stage2_build_symbols()
    an.stage3_cha_and_overrides()
    an.stage3b_implements()
    an.stage4_calls_and_news()
    an.stage5_type_usage()

    # dump nodes/edges
    with open(out/"nodes.jsonl","w") as f:
        for n in an.nodes: f.write(json.dumps(n)+"\n")
    with open(out/"edges.jsonl","w") as f:
        for e in an.edges: f.write(json.dumps(e)+"\n")

    # dot
    to_dot(an.nodes, an.edges, str(out/"dep"), str(out/"dep"))

    # quick counts
    from collections import Counter
    c = Counter(e["label"] for e in an.edges)
    print("Edge counts:", dict(c))
    print("Wrote:", out)

    # Verify metadata completeness
    verify_metadata_completeness(an.nodes)


def verify_metadata_completeness(nodes):
    """Verify all nodes have required metadata fields"""
    print("\nVerifying metadata completeness...")

    issues = []
    for node in nodes:
        node_id = node["id"]
        metadata = node.get("metadata", {})

        # Check file_path
        if not metadata.get("file_path"):
            issues.append(f"{node_id}: missing file_path")

        # Check line_range
        if not metadata.get("line_range"):
            issues.append(f"{node_id}: missing line_range")

        # For methods, check additional fields
        if node_id.startswith("method:"):
            if not metadata.get("return_type") and metadata.get("return_type") is not None:
                # return_type can be None for constructors, so only check if it's missing entirely
                pass
            if "params" not in metadata:
                issues.append(f"{node_id}: missing params")
            if not metadata.get("source_code"):
                issues.append(f"{node_id}: missing source_code")

    if issues:
        print(f"WARNING: Found {len(issues)} metadata issues:")
        for issue in issues[:10]:  # Show first 10
            print(f"   - {issue}")
        if len(issues) > 10:
            print(f"   ... and {len(issues) - 10} more")
    else:
        print("OK: All nodes have complete metadata")

    return len(issues) == 0

if __name__ == "__main__":
    main()
