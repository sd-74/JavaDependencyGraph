import json, sys
from pathlib import Path
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
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


    # print("Sample method:", json.dumps(files[0]["symbols"]["methods"][0], indent=2))
    # print("Sample stmt:", json.dumps(files[0]["symbols"]["stmts"][0], indent=2))

if __name__ == "__main__":
    main()
