from graphviz import Digraph
import os

def _escape_dot_id(node_id: str) -> str:
    """Escape special characters in DOT node IDs"""
    # Replace colons and other special characters with underscores
    return node_id.replace(":", "_").replace("#", "_").replace("(", "_").replace(")", "_").replace("<", "_").replace(">", "_")

def to_dot(nodes: list[dict], edges: list[dict], out_png: str, out_svg: str):
    try:
        g = Digraph("dep", format="png")
        g.attr("node", shape="box", style="filled", fillcolor="#cfe8f3")
        
        # Create mapping from original IDs to escaped IDs
        id_mapping = {}
        for n in nodes:
            escaped_id = _escape_dot_id(n["id"])
            id_mapping[n["id"]] = escaped_id
            g.node(escaped_id, n["label"])
        
        # edges - use escaped IDs
        for e in edges:
            src_escaped = id_mapping[e["src"]]
            dst_escaped = id_mapping[e["dst"]]
            g.edge(src_escaped, dst_escaped, label=e["label"])
        
        g.render(out_png, cleanup=True)
        g.format = "svg"
        g.render(out_svg, cleanup=True)
        print(f"Generated graphs: {out_png}.png and {out_svg}.svg")
    except Exception as e:
        print(f"Warning: Could not generate graphs: {e}")
        print("Make sure Graphviz is installed and available in PATH")
