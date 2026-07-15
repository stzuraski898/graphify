#!/usr/bin/env python3
"""Apply type deduplication to existing Ceph graph and regenerate HTML."""

import json
import sys
from pathlib import Path

# Add graphify to path
sys.path.insert(0, str(Path(__file__).parent))

from graphify.dedup_types import deduplicate_common_types, FRAMEWORK_TYPES
from graphify.build import build_from_json
# from graphify.export import write_graph_json  # Not needed
import networkx as nx

# Ceph-specific types to deduplicate
CEPH_TYPES = {
    "bufferlist", "Context", "Formatter",
    "epoch_t", "utime_t", "entity_addr_t",
    "entity_addrvec_t", "entity_name_t",
    "ceph_tid_t", "pg_t", "spg_t",
    "CephContext", "MonClient", "Objecter",
    "Connection", "Message", "ref_t",
}

# Update the framework types
FRAMEWORK_TYPES.update(CEPH_TYPES)

def main():
    ceph_graph_path = Path.home() / "ceph/src/mgr/graphify-out/graph.json"
    
    if not ceph_graph_path.exists():
        print(f"Error: {ceph_graph_path} not found")
        return 1
    
    print(f"Loading graph from {ceph_graph_path}...")
    with open(ceph_graph_path) as f:
        graph_data = json.load(f)
    
    # Build NetworkX graph
    print("Building NetworkX graph...")
    G = build_from_json(graph_data, directed=True)
    
    print(f"Original graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # Apply deduplication
    print("\nApplying type deduplication...")
    G_dedup = deduplicate_common_types(G, verbose=True)
    
    print(f"\nDeduplicated graph: {G_dedup.number_of_nodes()} nodes, {G_dedup.number_of_edges()} edges")
    print(f"Reduction: {G.number_of_nodes() - G_dedup.number_of_nodes()} nodes removed")
    
    # Save deduplicated graph
    output_path = ceph_graph_path.parent / "graph-dedup.json"
    print(f"\nSaving deduplicated graph to {output_path}...")
    
    # Convert back to dict format
    nodes = []
    for node_id, attrs in G_dedup.nodes(data=True):
        node = {"id": node_id}
        node.update(attrs)
        nodes.append(node)
    
    edges = []
    for src, dst, attrs in G_dedup.edges(data=True):
        edge = {"source": src, "target": dst}
        edge.update(attrs)
        edges.append(edge)
    
    dedup_data = {
        "nodes": nodes,
        "edges": edges,
        "metadata": graph_data.get("metadata", {}),
    }
    
    with open(output_path, 'w') as f:
        json.dump(dedup_data, f, indent=2)
    
    print(f"Saved to {output_path}")
    
    # Generate HTML visualizations
    print("\nGenerating HTML visualizations...")
    
    # Generate force-directed graph
    try:
        from graphify.callflow_html import write_callflow_html
        html_path = ceph_graph_path.parent / "graph-dedup.html"
        print(f"Generating force-directed graph: {html_path}")
        
        # Use the simpler approach - just copy and modify the existing HTML
        original_html = ceph_graph_path.parent / "graph.html"
        if original_html.exists():
            print(f"Reading original HTML from {original_html}")
            html_content = original_html.read_text()
            
            # Replace the graph data
            import re
            # Find the RAW_NODES and LEGEND data
            nodes_match = re.search(r'const RAW_NODES = \[.*?\];', html_content, re.DOTALL)
            if nodes_match:
                # Create new nodes JSON
                nodes_json = json.dumps(nodes, separators=(',', ':'))
                new_nodes_line = f"const RAW_NODES = {nodes_json};"
                html_content = html_content[:nodes_match.start()] + new_nodes_line + html_content[nodes_match.end():]
            
            # Write the modified HTML
            html_path.write_text(html_content)
            print(f"Saved deduplicated HTML to {html_path}")
    except Exception as e:
        print(f"Warning: Could not generate HTML: {e}")
    
    # Generate tree view
    try:
        from graphify.tree_html import write_tree_html
        tree_path = ceph_graph_path.parent / "graph-dedup-topdown.html"
        print(f"Generating tree view: {tree_path}")
        write_tree_html(
            output_path,
            tree_path,
            project_label="Ceph MGR (Deduplicated)"
        )
        print(f"Saved tree view to {tree_path}")
    except Exception as e:
        print(f"Warning: Could not generate tree HTML: {e}")
    
    print("\n✅ Deduplication complete!")
    print(f"\nResults:")
    print(f"  - Original: {G.number_of_nodes()} nodes")
    print(f"  - Deduplicated: {G_dedup.number_of_nodes()} nodes")
    print(f"  - Reduction: {G.number_of_nodes() - G_dedup.number_of_nodes()} nodes ({100 * (G.number_of_nodes() - G_dedup.number_of_nodes()) / G.number_of_nodes():.1f}%)")
    print(f"\nFiles created:")
    print(f"  - {output_path}")
    print(f"  - {ceph_graph_path.parent / 'graph-dedup.html'}")
    print(f"  - {ceph_graph_path.parent / 'graph-dedup-topdown.html'}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
