# Ceph Graphify Visualization Improvements

## Summary

This document summarizes the improvements made to graphify's visualization capabilities when applied to large codebases like Ceph (2,021 nodes, 3,543 edges).

## Problem Statement

The original Ceph MGR graphify output had several readability issues:
1. **Duplicate data clutter** - Common types like `string` (41 instances), `map` (10 instances) appeared repeatedly
2. **Small unreadable text** - 13px font was too small for complex graphs
3. **Visual noise** - File extensions (.cc, .h) and inline counts cluttered node labels
4. **Graph hairball** - 2,000+ nodes in one view made it impossible to focus on specific components

## Solutions Implemented

### 1. Type Deduplication

**Script**: `apply_dedup_to_ceph.py`

Applied selective deduplication to merge common stdlib and framework types:

**Results**:
- Nodes: 2,021 → 1,764 (257 removed, 12.7% reduction)
- File size: 1.2MB → 1.0MB (16.7% reduction)
- 47 common types merged into canonical `stdlib_*` nodes

**Types deduplicated**:
- C++ STL: `string`, `map`, `vector`, `set`, `list`, `pair`, `shared_ptr`, `unique_ptr`, `function`, `optional`, `variant`, `tuple`
- Python C API: `PyObject`, `PyTypeObject`, `PyMethodDef`, `PyModuleDef`
- Ceph framework: `Context`, `Finisher`, `Messenger`, `OSDMap`, `PGMap`, `MonMap`

**Preserved**:
- Application classes (DaemonServer, ActivePyModules, MgrClient, etc.)
- All edges and relationships
- File-specific implementations

### 2. Enhanced Tree View

**File**: `graphify/tree_html.py`

Improved typography and layout for better readability:

**Changes**:
- Font size: 13px → 18px (38% larger)
- Font weight: normal → 600 (semi-bold)
- Text color: #333 → #1a1a1a (darker, better contrast)
- Removed file extensions (.cc, .h, .cpp)
- Moved counts to separate badge lines
- Increased spacing: 40px → 50px vertical, 400px → 450px horizontal
- Larger circles: 8px → 10px radius

**Usage**:
```bash
# Generated automatically with graphify
firefox graphify-out/graph-topdown.html &
```

### 3. Focused Graph View (NEW)

**Files**: 
- `graphify/focused_graph_html.py` (438 lines)
- `scripts/generate_focused_graph.py` (130 lines)
- `docs/focused-graph-view.md` (283 lines)

**The Solution for Large Codebases**

Shows **one node and its connections at a time** instead of all 2,000+ nodes:

**Features**:
- ✅ Force-directed layout with vis-network
- ✅ Color-coded: Red (selected), Blue (incoming), Green (outgoing)
- ✅ Search with autocomplete
- ✅ Click nodes to refocus
- ✅ Draggable nodes with physics simulation
- ✅ Dark background (#4a4a4a) for better contrast
- ✅ Connection counts in real-time

**Usage**:
```bash
# From default location
python scripts/generate_focused_graph.py

# From deduplicated graph (recommended)
python scripts/generate_focused_graph.py --graph graphify-out/graph-dedup.json

# Custom paths
python scripts/generate_focused_graph.py \
  --graph path/to/graph.json \
  --output path/to/output.html \
  --project "My Project"
```

**Example workflow**:
1. Search for "DaemonServer"
2. See 105 outgoing connections (green) - what it calls
3. See 1 incoming connection (blue) - what calls it
4. Click on "ActivePyModules" to explore its connections
5. Drag nodes to create custom layout
6. Take screenshot for documentation

## Comparison of Visualization Types

### Full Force-Directed Graph (`graph.html`)
- ✅ Shows everything at once
- ✅ Good for overall structure
- ❌ Cluttered with 1000+ nodes
- ❌ Hard to focus on specific components

### Tree View (`graph-topdown.html`)
- ✅ Shows file hierarchy
- ✅ Good for understanding structure
- ✅ Now with better typography
- ❌ Doesn't show relationships between files
- ❌ No call flow information

### Focused Graph View (`graph-focused.html`) ⭐ NEW
- ✅ Clean, uncluttered view
- ✅ Easy to explore specific components
- ✅ Shows relationships and call flows
- ✅ Draggable for custom layouts
- ✅ Interactive exploration
- ❌ Only shows one node at a time

### Callflow Diagram (`graph-callflow.html`)
- ✅ Shows architecture with Mermaid diagrams
- ✅ Good for documentation
- ❌ Static, pre-generated sections
- ❌ Limited to top N nodes

## Technical Details

### Deduplication Strategy

**Advantages**:
- Reduces visual clutter
- Preserves application-specific classes
- Maintains all relationships
- File size reduction

**Disadvantages** (see `DEDUPLICATION_STRATEGY_DISADVANTAGES.md`):
- Loss of file-specific context
- Harder to trace specific implementations
- May hide polymorphism
- Complicates debugging
- Affects graph metrics
- Can obscure architectural patterns
- Makes incremental updates harder
- Reduces precision in queries
- May hide version conflicts
- Complicates cross-language analysis

### Focused Graph Physics

Uses vis-network with ForceAtlas2Based solver:
- **Gravitational constant**: -150 (strong repulsion)
- **Spring length**: 350 (long connections)
- **Spring constant**: 0.02 (weak springs)
- **Central gravity**: 0.005 (minimal pull to center)
- **Damping**: 0.4 (smooth movement)

### Performance

- Pre-computed connection index for instant display
- Only renders visible nodes (1 + N connections)
- Efficient even with 10,000+ node graphs
- No LLM calls, fully local

## Files Created/Modified

### New Files
1. `DEDUPLICATION_STRATEGY_DISADVANTAGES.md` (398 lines) - Comprehensive analysis
2. `CEPH_DEDUPLICATION_RESULTS.md` (213 lines) - Before/after comparison
3. `apply_dedup_to_ceph.py` (135 lines) - Reusable deduplication script
4. `graphify/focused_graph_html.py` (438 lines) - Focused view generator
5. `scripts/generate_focused_graph.py` (130 lines) - CLI script
6. `docs/focused-graph-view.md` (283 lines) - User documentation
7. `CEPH_VISUALIZATION_IMPROVEMENTS.md` (this file)

### Modified Files
1. `graphify/tree_html.py` - Enhanced typography and layout
2. `README.md` - Added focused graph view section

## Recommendations

### For Large Codebases (1000+ nodes)

1. **Always use deduplication**:
   ```bash
   python apply_dedup_to_ceph.py
   ```

2. **Use focused graph view for exploration**:
   ```bash
   python scripts/generate_focused_graph.py --graph graphify-out/graph-dedup.json
   ```

3. **Start with highly connected nodes** - They appear first in search

4. **Drag nodes to organize** - Create your own mental model

### For Code Review

1. Search for changed files in focused view
2. Check incoming connections (what will be affected?)
3. Check outgoing connections (what dependencies changed?)
4. Use tree view to understand file structure

### For Onboarding

1. Start with main entry points (search for "main", "Server", "Manager")
2. Follow the call chain by clicking through connections
3. Drag nodes to create a map as you learn
4. Take screenshots for documentation

## Next Steps

Potential future improvements:
1. Add focused view to main graphify CLI as `graphify focused-graph` command
2. Add export functionality (save custom layouts)
3. Add filtering by edge type (calls, imports, inherits)
4. Add community coloring to focused view
5. Add path highlighting between two nodes
6. Add "expand all" mode to show N-hop neighborhoods

## See Also

- [DEDUPLICATION_STRATEGY_DISADVANTAGES.md](DEDUPLICATION_STRATEGY_DISADVANTAGES.md) - Full analysis of deduplication tradeoffs
- [CEPH_DEDUPLICATION_RESULTS.md](CEPH_DEDUPLICATION_RESULTS.md) - Detailed before/after metrics
- [docs/focused-graph-view.md](docs/focused-graph-view.md) - User guide for focused view
- [README.md](README.md) - Main graphify documentation