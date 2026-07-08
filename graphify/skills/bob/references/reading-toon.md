# Reading TOON Graph Files

When `graphify-out/graph.toon` exists, prefer reading it over `graph.json` for better token efficiency (33-41% smaller).

## Reading TOON Files (Recommended)

The TOON decoder is now available in Graphify:

```python
from pathlib import Path
from networkx.readwrite import json_graph
from graphify.toon import decode as toon_decode
import json

# Prefer TOON if available (33-41% smaller)
toon_path = Path('graphify-out/graph.toon')
json_path = Path('graphify-out/graph.json')

if toon_path.exists():
    data = toon_decode(toon_path.read_text())
else:
    data = json.loads(json_path.read_text())

G = json_graph.node_link_graph(data, edges='links')
```

## Fallback Approach (JSON)

If you prefer to use JSON only:

```python
import json
from pathlib import Path
from networkx.readwrite import json_graph

# Read graph from JSON
data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')
```

## Direct Reading (LLMs)

When you need to read graph data directly into your context (not through Python), always prefer `graph.toon`:

1. Check if `graphify-out/graph.toon` exists
2. If yes, read it (33% fewer tokens than JSON)
3. If no, fall back to `graphify-out/graph.json`

Both files contain identical data - TOON is just a more token-efficient encoding.

## TOON Format Overview

TOON uses:
- Tabular format for uniform arrays (nodes, edges)
- Indentation instead of braces
- Minimal quoting
- Explicit array lengths and field declarations

Example:
```toon
nodes[3]{id,label,type}:
  node1,Function A,function
  node2,Function B,function
  node3,Class C,class
edges[2]{source,target,relation}:
  node1,node2,calls
  node2,node3,uses
```

vs JSON:
```json
{
  "nodes": [
    {"id": "node1", "label": "Function A", "type": "function"},
    {"id": "node2", "label": "Function B", "type": "function"},
    {"id": "node3", "label": "Class C", "type": "class"}
  ],
  "edges": [
    {"source": "node1", "target": "node2", "relation": "calls"},
    {"source": "node2", "target": "node3", "relation": "uses"}
  ]
}