# Focused Graph View

An interactive force-directed graph visualization that shows **one node and its connections at a time**, making it easy to explore large codebases without visual clutter.

## Overview

The focused graph view addresses a common problem with large codebase visualizations: when you have thousands of nodes, the graph becomes an unreadable hairball. This view solves that by:

1. **Showing only one node at a time** - Select a class/file to see just its connections
2. **Color-coding relationships** - Red (selected), Blue (incoming), Green (outgoing)
3. **Interactive exploration** - Click any connected node to make it the new focus
4. **Draggable layout** - Arrange nodes however you like
5. **Smart search** - Find nodes by name with autocomplete

## Quick Start

### Generate the View

```bash
# From default location
python scripts/generate_focused_graph.py

# From deduplicated graph (recommended for large codebases)
python scripts/generate_focused_graph.py --graph graphify-out/graph-dedup.json

# Custom paths
python scripts/generate_focused_graph.py \
  --graph path/to/graph.json \
  --output path/to/output.html \
  --project "My Project"
```

### Open in Browser

```bash
firefox graphify-out/graph-focused.html &
```

## Features

### 🎯 One Node at a Time

Instead of showing all 2,000+ nodes at once, the focused view shows:
- **1 selected node** (red, center) - The class/file you're examining
- **N incoming nodes** (blue) - Who calls this node's functions
- **M outgoing nodes** (green) - What functions this node calls

This makes even highly connected nodes (100+ connections) readable and explorable.

### 🔍 Smart Search

Type to search for any class or file:
- Autocomplete suggestions as you type
- Shows connection counts for each result
- Sorted by most connected first
- Searches both class names and file paths

### 🎨 Color Coding

- **Red** - Selected node (the one you're examining)
- **Blue** - Incoming connections (these nodes call the selected node)
- **Green** - Outgoing connections (selected node calls these nodes)
- **Dark gray background** - Better contrast for colored nodes

### 🖱️ Interactive Controls

**Drag Nodes**
- Click and drag any node to reposition it
- Nodes stay where you put them
- Arrange the layout however makes sense to you

**Navigate**
- Click any connected node to make it the new focus
- Zoom with mouse wheel
- Pan by dragging empty space

**Search**
- Type in the search box to find nodes
- Click a suggestion to focus on that node

### 📊 Info Bar

Shows real-time information about the selected node:
- Node name
- Number of incoming connections
- Number of outgoing connections
- Total connections

## Use Cases

### Understanding Architecture

**Question**: "What does DaemonServer interact with?"

1. Search for "DaemonServer"
2. See all its incoming and outgoing connections
3. Click on interesting connections to explore further

### Tracing Dependencies

**Question**: "What calls this function?"

1. Search for the function/class
2. Blue nodes show all callers
3. Click a caller to see what *it* depends on

### Finding Usage

**Question**: "Where is this class used?"

1. Search for the class
2. Incoming connections (blue) show all usage sites
3. Click through to explore the call chain

### Code Review

**Question**: "What's the impact of changing this class?"

1. Search for the class
2. Incoming connections show what will be affected
3. Outgoing connections show what it depends on

## Comparison with Other Views

### vs. Full Force-Directed Graph

**Full Graph** (`graph.html`):
- ✅ Shows everything at once
- ✅ Good for seeing overall structure
- ❌ Cluttered with 1000+ nodes
- ❌ Hard to focus on specific components

**Focused Graph** (`graph-focused.html`):
- ✅ Clean, uncluttered view
- ✅ Easy to explore specific components
- ✅ Draggable for custom layouts
- ❌ Only shows one node at a time

### vs. Tree View

**Tree View** (`graph-topdown.html`):
- ✅ Shows file hierarchy
- ✅ Good for understanding structure
- ❌ Doesn't show relationships between files
- ❌ No call flow information

**Focused Graph**:
- ✅ Shows relationships and call flows
- ✅ Interactive exploration
- ❌ Doesn't show file hierarchy

### vs. Callflow Diagram

**Callflow** (`graph-callflow.html`):
- ✅ Shows architecture with Mermaid diagrams
- ✅ Good for documentation
- ❌ Static, pre-generated sections
- ❌ Limited to top N nodes

**Focused Graph**:
- ✅ Explore any node on demand
- ✅ Interactive, real-time
- ❌ No diagram export

## Best Practices

### For Large Codebases

1. **Use deduplicated graph** - Removes stdlib noise
   ```bash
   python scripts/generate_focused_graph.py --graph graphify-out/graph-dedup.json
   ```

2. **Start with highly connected nodes** - They're listed first in search

3. **Drag nodes to organize** - Create your own mental model of the architecture

### For Code Review

1. **Search for changed files** - See their connections
2. **Check incoming connections** - What will be affected?
3. **Check outgoing connections** - What dependencies changed?

### For Onboarding

1. **Start with main entry points** - Search for "main", "App", "Server"
2. **Follow the call chain** - Click through connections
3. **Drag to create a map** - Organize nodes as you learn

## Technical Details

### Physics Simulation

The graph uses a force-directed layout with:
- **Strong repulsion** - Nodes push each other apart (gravitationalConstant: -150)
- **Long springs** - Connections are stretched out (springLength: 350)
- **Weak springs** - Nodes spread more (springConstant: 0.02)
- **Low central gravity** - Less pull to center (centralGravity: 0.005)
- **Damping** - Smooth movement (damping: 0.4)

### Node Filtering

- Stdlib nodes (string, map, vector, etc.) are excluded from the search list
- But their connections are still counted and shown
- This keeps the view focused on application code

### Performance

- Pre-computed connection index for instant display
- Only renders visible nodes (1 + N connections)
- Efficient even with 10,000+ node graphs

## Troubleshooting

### "No connections shown"

- Check that the graph has edges (not just nodes)
- Try a different node - some may have no connections
- Verify the graph.json is valid

### "Search returns no results"

- Check spelling
- Try partial matches (e.g., "Daemon" instead of "DaemonServer")
- Verify nodes exist in the graph

### "Graph is still cluttered"

- Some nodes have 100+ connections (e.g., DaemonServer)
- Drag nodes to spread them out
- Zoom out to see the full layout
- Consider using the deduplicated graph

### "Nodes won't stay in place"

- Physics is still running - wait for stabilization
- Drag a node to "pin" it in place
- Refresh the page to reset

## Examples

### Example 1: Exploring DaemonServer

```bash
# Generate focused view
python scripts/generate_focused_graph.py --graph graphify-out/graph-dedup.json

# Open in browser
firefox graphify-out/graph-dedup-focused.html &
```

1. Search for "DaemonServer"
2. See 105 outgoing connections (green) - what DaemonServer calls
3. See 1 incoming connection (blue) - what calls DaemonServer
4. Click on "ActivePyModules" to see what *it* connects to

### Example 2: Finding All Callers

```bash
# Generate from original graph (more detail)
python scripts/generate_focused_graph.py --graph graphify-out/graph.json
```

1. Search for your function/class
2. Blue nodes = all callers
3. Click through to trace the call chain back to entry points

### Example 3: Custom Layout

1. Search for a central class
2. Drag incoming nodes to the left
3. Drag outgoing nodes to the right
4. Create a left-to-right flow diagram
5. Take a screenshot for documentation

## See Also

- [Deduplication Strategy](../DEDUPLICATION_STRATEGY_DISADVANTAGES.md) - Why and how to deduplicate
- [Tree View](tree-html.md) - File hierarchy visualization
- [Callflow Diagrams](callflow-html.md) - Architecture documentation
- [Main README](../README.md) - Full graphify documentation