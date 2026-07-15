"""Post-processing deduplication for common language types.

Merges file-scoped nodes for built-in/standard library types into single
canonical nodes while preserving file-specific nodes for user-defined symbols.
This reduces graph clutter from types like 'string', 'map', 'vector' that
appear in every file, while maintaining the context-rich file-scoped IDs for
actual application code.
"""
from __future__ import annotations
import networkx as nx
from typing import Set

# Common C++ standard library types that should be deduplicated
CPP_STDLIB_TYPES: Set[str] = {
    # Containers
    "vector", "list", "deque", "array", "forward_list",
    "set", "multiset", "unordered_set", "unordered_multiset",
    "map", "multimap", "unordered_map", "unordered_multimap",
    "stack", "queue", "priority_queue",
    
    # Strings
    "string", "wstring", "u16string", "u32string", "string_view",
    
    # Smart pointers
    "unique_ptr", "shared_ptr", "weak_ptr",
    
    # Utilities
    "pair", "tuple", "optional", "variant", "any",
    "function", "reference_wrapper",
    
    # Iterators
    "iterator", "const_iterator", "reverse_iterator",
    
    # Threading
    "thread", "mutex", "shared_mutex", "condition_variable",
    "atomic", "lock_guard", "unique_lock",
    
    # Streams
    "ostream", "istream", "iostream", "stringstream",
    "ifstream", "ofstream", "fstream",
    
    # Other common
    "span", "byte", "duration", "time_point",
}

# Python built-in types
PYTHON_BUILTIN_TYPES: Set[str] = {
    "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "frozenset", "complex",
}

# Common framework types (can be extended per project)
FRAMEWORK_TYPES: Set[str] = {
    # Ceph-specific common types
    "bufferlist", "Context", "Formatter", "epoch_t", "utime_t",
    "entity_addr_t", "entity_addrvec_t", "entity_name_t",
    "ceph_tid_t", "pg_t", "spg_t",
    
    # Python C API
    "PyObject", "PyThreadState", "PyTypeObject",
    
    # Generic
    "Connection", "Message", "ref_t",
}

ALL_DEDUP_TYPES = CPP_STDLIB_TYPES | PYTHON_BUILTIN_TYPES | FRAMEWORK_TYPES


def should_deduplicate(label: str) -> bool:
    """Check if a node label should be deduplicated across files."""
    return label.lower() in {t.lower() for t in ALL_DEDUP_TYPES}


def deduplicate_common_types(G: nx.Graph | nx.DiGraph, verbose: bool = False) -> nx.Graph | nx.DiGraph:
    """Merge file-scoped nodes for common types into canonical nodes.
    
    Args:
        G: Input graph with file-scoped node IDs
        verbose: Print deduplication statistics
        
    Returns:
        New graph with common types deduplicated
    """
    # Group nodes by normalized label
    label_groups: dict[str, list[str]] = {}
    
    for node_id, attrs in G.nodes(data=True):
        label = attrs.get("label", "")
        norm_label = label.lower()
        
        if should_deduplicate(label):
            if norm_label not in label_groups:
                label_groups[norm_label] = []
            label_groups[norm_label].append(node_id)
    
    if verbose:
        print(f"Found {len(label_groups)} common types to deduplicate")
        total_nodes = sum(len(nodes) for nodes in label_groups.values())
        print(f"  Total duplicate nodes: {total_nodes}")
        print(f"  Will reduce to: {len(label_groups)} canonical nodes")
    
    # Create new graph (use DiGraph to support directed edges)
    H = nx.DiGraph() if G.is_directed() else nx.Graph()
    
    # Copy all nodes first
    for node_id, attrs in G.nodes(data=True):
        H.add_node(node_id, **attrs)
    
    # Copy all edges
    for src, dst, attrs in G.edges(data=True):
        H.add_edge(src, dst, **attrs)
    
    # For each group, merge into canonical node
    for norm_label, node_ids in label_groups.items():
        if len(node_ids) <= 1:
            continue
            
        # Use first node as canonical, or create new one
        canonical_id = f"stdlib_{norm_label}"
        canonical_attrs = {
            "label": node_ids[0].split("_")[-1],  # Extract original label
            "file_type": "code",
            "source_file": "",
            "source_location": "",
            "_origin": "stdlib",
            "norm_label": norm_label,
            "_deduplicated_from": len(node_ids),
        }
        
        # Collect all edges from duplicate nodes
        all_edges = []
        for node_id in node_ids:
            # Collect edges based on graph type
            if isinstance(H, nx.DiGraph):
                # Incoming edges
                for pred in list(H.predecessors(node_id)):
                    edge_data = H.get_edge_data(pred, node_id)
                    all_edges.append((pred, canonical_id, edge_data))
                
                # Outgoing edges
                for succ in list(H.successors(node_id)):
                    edge_data = H.get_edge_data(node_id, succ)
                    all_edges.append((canonical_id, succ, edge_data))
            else:
                # For undirected graphs, check neighbors
                for neighbor in list(H.neighbors(node_id)):
                    edge_data = H.get_edge_data(node_id, neighbor)
                    all_edges.append((canonical_id, neighbor, edge_data))
            
            # Remove old node
            if node_id in H:
                H.remove_node(node_id)
        
        # Add canonical node
        H.add_node(canonical_id, **canonical_attrs)
        
        # Add deduplicated edges (removing duplicates)
        edge_set = set()
        for src, dst, data in all_edges:
            edge_key = (src, dst, data.get("relation") if data else None)
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                H.add_edge(src, dst, **(data or {}))
    
    if verbose:
        orig_nodes = G.number_of_nodes()
        new_nodes = H.number_of_nodes()
        print(f"Graph reduced from {orig_nodes} to {new_nodes} nodes "
              f"({orig_nodes - new_nodes} removed)")
    
    return H


def add_dedup_config_option(config: dict) -> dict:
    """Add deduplication configuration to .graphify.toml schema.
    
    Example config:
        [deduplication]
        enabled = true
        types = ["string", "vector", "map"]  # Additional types to deduplicate
        exclude = ["MyString"]  # Types to never deduplicate
    """
    if "deduplication" not in config:
        config["deduplication"] = {
            "enabled": False,
            "additional_types": [],
            "exclude_types": [],
        }
    return config

# Made with Bob
