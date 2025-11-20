"""
Extract focused subgraphs from the full dependency graph.
"""

from typing import List, Dict, Set
from collections import defaultdict


class SubgraphExtractor:
    def __init__(self, nodes: List[Dict], edges: List[Dict]):
        """Initialize with full dependency graph"""
        self.all_nodes = {n["id"]: n for n in nodes}
        self.all_edges = edges

        # Build adjacency lists for efficient traversal
        self.outgoing = defaultdict(list)  # src -> [(label, dst)]
        self.incoming = defaultdict(list)  # dst -> [(label, src)]

        for edge in edges:
            self.outgoing[edge["src"]].append((edge["label"], edge["dst"]))
            self.incoming[edge["dst"]].append((edge["label"], edge["src"]))

    def extract_focused_subgraph(
        self,
        seed_node_ids: Set[str],
        include_dependencies: bool = True,
        include_dependents: bool = True,
        max_depth: int = 2
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Extract a focused subgraph starting from seed nodes.

        Args:
            seed_node_ids: Starting nodes (mandate-relevant nodes)
            include_dependencies: Include nodes that seed nodes depend on
            include_dependents: Include nodes that depend on seed nodes
            max_depth: Maximum traversal depth in each direction

        Returns:
            (nodes, edges) - Subgraph nodes and edges
        """
        relevant_nodes = set(seed_node_ids)

        # Expand to include dependencies (what these nodes use/call)
        if include_dependencies:
            relevant_nodes.update(
                self._traverse(seed_node_ids, self.outgoing, max_depth,
                              edge_types=["Calls", "Uses", "Instantiates", "BaseClassOf", "Implements"])
            )

        # Expand to include dependents (what uses/calls these nodes)
        if include_dependents:
            relevant_nodes.update(
                self._traverse(seed_node_ids, self.incoming, max_depth,
                              edge_types=["CalledBy", "UsedBy", "InstantiatedBy", "DerivedClassOf", "ImplementedBy"])
            )

        # Extract nodes and edges for the subgraph
        subgraph_nodes = [self.all_nodes[nid] for nid in relevant_nodes if nid in self.all_nodes]
        subgraph_edges = [
            e for e in self.all_edges
            if e["src"] in relevant_nodes and e["dst"] in relevant_nodes
        ]

        print(f"📊 Subgraph: {len(subgraph_nodes)} nodes, {len(subgraph_edges)} edges")

        return subgraph_nodes, subgraph_edges

    def _traverse(
        self,
        start_nodes: Set[str],
        adjacency: Dict[str, List],
        max_depth: int,
        edge_types: List[str]
    ) -> Set[str]:
        """BFS traversal to find connected nodes"""
        visited = set()
        queue = [(node, 0) for node in start_nodes]

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue

            visited.add(current)

            # Add neighbors based on edge type filter
            for label, neighbor in adjacency[current]:
                if label in edge_types and neighbor not in visited:
                    queue.append((neighbor, depth + 1))

        return visited

