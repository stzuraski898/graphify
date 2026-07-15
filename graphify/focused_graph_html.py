"""Focused graph view - shows one node and its connections at a time.

Similar to the force-directed graph, but with a node selector that filters
to show only the selected node and its immediate neighbors.
"""
from __future__ import annotations

import html as _html
import json
from pathlib import Path
from typing import Any, Dict


def build_node_index(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Build searchable index of nodes with their connections."""
    nodes_by_id = {n['id']: n for n in graph.get('nodes', [])}
    
    # Build adjacency lists - initialize ALL nodes first
    node_connections = {}
    for node in graph.get('nodes', []):
        node_id = node['id']
        node_connections[node_id] = {
            'node': node,
            'incoming': [],
            'outgoing': [],
            'neighbors': set()
        }
    
    # Handle both 'edges' and 'links' formats
    edges = graph.get('edges', []) or graph.get('links', [])
    for edge in edges:
        src = edge.get('source')
        tgt = edge.get('target')
        
        if not src or not tgt:
            continue
            
        if src in node_connections:
            node_connections[src]['outgoing'].append({
                'target': tgt,
                'relation': edge.get('relation', 'unknown'),
                'edge': edge
            })
            node_connections[src]['neighbors'].add(tgt)
            
        if tgt in node_connections:
            node_connections[tgt]['incoming'].append({
                'source': src,
                'relation': edge.get('relation', 'unknown'),
                'edge': edge
            })
            node_connections[tgt]['neighbors'].add(src)
    
    # Convert sets to lists for JSON serialization
    for node_id in node_connections:
        node_connections[node_id]['neighbors'] = list(node_connections[node_id]['neighbors'])
    
    # Convert to list for easier JavaScript handling (skip stdlib nodes in list)
    node_list = []
    for node_id, data in node_connections.items():
        if node_id.startswith('stdlib_'):
            continue
        node_list.append({
            'id': node_id,
            'label': data['node'].get('label', node_id),
            'file': data['node'].get('source_file', ''),
            'incoming_count': len(data['incoming']),
            'outgoing_count': len(data['outgoing']),
            'total_connections': len(data['neighbors'])
        })
    
    # Sort by total connections (most connected first)
    node_list.sort(key=lambda x: x['total_connections'], reverse=True)
    
    return {
        'nodes': nodes_by_id,
        'connections': node_connections,
        'node_list': node_list
    }


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{
      font-family: 'Segoe UI', sans-serif;
      margin: 0;
      padding: 0;
      background: #4a4a4a;
      color: #333;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }}
    .header {{
      background: #fff;
      padding: 20px 24px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    h1 {{
      margin: 0 0 15px 0;
      font-size: 2rem;
      font-weight: bold;
      color: #1e3a56;
    }}
    .controls {{
      display: flex;
      gap: 15px;
      align-items: center;
    }}
    .node-selector {{
      flex: 1;
      max-width: 600px;
    }}
    .node-selector input {{
      width: 100%;
      padding: 10px 15px;
      font-size: 1rem;
      border: 2px solid #ddd;
      border-radius: 5px;
      transition: border-color 0.2s;
    }}
    .node-selector input:focus {{
      outline: none;
      border-color: #007bff;
    }}
    .suggestions {{
      position: absolute;
      background: #fff;
      border: 2px solid #007bff;
      border-top: none;
      border-radius: 0 0 5px 5px;
      max-height: 300px;
      overflow-y: auto;
      width: 600px;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      display: none;
      z-index: 1000;
    }}
    .suggestions.visible {{
      display: block;
    }}
    .suggestion-item {{
      padding: 10px 15px;
      cursor: pointer;
      border-bottom: 1px solid #eee;
    }}
    .suggestion-item:hover {{
      background: #f0f8ff;
    }}
    .suggestion-label {{
      font-weight: 600;
      color: #1a1a1a;
    }}
    .suggestion-meta {{
      font-size: 0.85rem;
      color: #666;
      margin-top: 3px;
    }}
    .info-bar {{
      padding: 10px 15px;
      background: #e3f2fd;
      border-radius: 5px;
      font-size: 0.9rem;
    }}
    .info-bar strong {{
      color: #1976d2;
    }}
    #graph-container {{
      flex: 1;
      position: relative;
      overflow: hidden;
      background: #4a4a4a;
    }}
    #graph {{
      width: 100%;
      height: 100%;
      background: #4a4a4a;
    }}
    .legend {{
      position: absolute;
      top: 20px;
      right: 20px;
      background: rgba(255,255,255,0.95);
      padding: 15px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      font-size: 0.9rem;
    }}
    .legend-title {{
      font-weight: 600;
      margin-bottom: 10px;
      color: #1e3a56;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      margin: 5px 0;
    }}
    .legend-color {{
      width: 20px;
      height: 20px;
      border-radius: 50%;
      margin-right: 8px;
      border: 2px solid #333;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>{header}</h1>
    <div class="controls">
      <div class="node-selector">
        <input 
          type="text" 
          id="node-search" 
          placeholder="Search for a class or file (e.g., DaemonServer)..."
          autocomplete="off"
        />
        <div id="suggestions" class="suggestions"></div>
      </div>
      <div class="info-bar" id="info-bar">
        Select a node to see its connections
      </div>
    </div>
  </div>
  <div id="graph-container">
    <div id="graph"></div>
    <div class="legend">
      <div class="legend-title">Legend</div>
      <div class="legend-item">
        <div class="legend-color" style="background: #e74c3c; border-color: #c0392b;"></div>
        <span>Selected Node</span>
      </div>
      <div class="legend-item">
        <div class="legend-color" style="background: #3498db; border-color: #2980b9;"></div>
        <span>Incoming (calls this)</span>
      </div>
      <div class="legend-item">
        <div class="legend-color" style="background: #2ecc71; border-color: #27ae60;"></div>
        <span>Outgoing (called by this)</span>
      </div>
    </div>
  </div>

  <script src="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js"></script>
  <script>
    const graphData = {graph_data};
    const nodeIndex = {node_index};
    
    let network = null;
    let currentNodeId = null;
    
    // Initialize with most connected node
    if (nodeIndex.node_list.length > 0) {{
      currentNodeId = nodeIndex.node_list[0].id;
      updateGraph(currentNodeId);
    }}
    
    // Search functionality
    const searchInput = document.getElementById('node-search');
    const suggestionsDiv = document.getElementById('suggestions');
    
    searchInput.addEventListener('input', (e) => {{
      const query = e.target.value.toLowerCase().trim();
      if (query.length < 2) {{
        suggestionsDiv.classList.remove('visible');
        return;
      }}
      
      const matches = nodeIndex.node_list.filter(n => 
        n.label.toLowerCase().includes(query) || 
        n.file.toLowerCase().includes(query)
      ).slice(0, 10);
      
      if (matches.length === 0) {{
        suggestionsDiv.classList.remove('visible');
        return;
      }}
      
      suggestionsDiv.innerHTML = matches.map(n => `
        <div class="suggestion-item" data-node-id="${{n.id}}">
          <div class="suggestion-label">${{n.label}}</div>
          <div class="suggestion-meta">
            ${{n.file ? n.file + ' • ' : ''}}
            ${{n.incoming_count}} incoming, ${{n.outgoing_count}} outgoing
          </div>
        </div>
      `).join('');
      
      suggestionsDiv.classList.add('visible');
      
      // Add click handlers
      suggestionsDiv.querySelectorAll('.suggestion-item').forEach(item => {{
        item.addEventListener('click', () => {{
          const nodeId = item.getAttribute('data-node-id');
          selectNode(nodeId);
          searchInput.value = '';
          suggestionsDiv.classList.remove('visible');
        }});
      }});
    }});
    
    // Close suggestions when clicking outside
    document.addEventListener('click', (e) => {{
      if (!searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {{
        suggestionsDiv.classList.remove('visible');
      }}
    }});
    
    function selectNode(nodeId) {{
      currentNodeId = nodeId;
      updateGraph(nodeId);
    }}
    
    function updateGraph(nodeId) {{
      const connections = nodeIndex.connections[nodeId];
      if (!connections) {{
        console.error('Node not found:', nodeId);
        return;
      }}
      
      const centerNode = connections.node;
      const nodes = [{{
        id: nodeId,
        label: centerNode.label || nodeId,
        color: {{ background: '#e74c3c', border: '#c0392b' }},
        size: 30,
        font: {{ size: 18, color: '#fff', face: 'Segoe UI', bold: true }}
      }}];
      
      const edges = [];
      const addedNodes = new Set([nodeId]);
      
      // Add incoming nodes (blue)
      connections.incoming.forEach(conn => {{
        const srcNode = nodeIndex.nodes[conn.source];
        if (srcNode && !addedNodes.has(conn.source)) {{
          nodes.push({{
            id: conn.source,
            label: srcNode.label || conn.source,
            color: {{ background: '#3498db', border: '#2980b9' }},
            size: 20,
            font: {{ size: 14, color: '#fff', face: 'Segoe UI' }}
          }});
          addedNodes.add(conn.source);
        }}
        edges.push({{
          from: conn.source,
          to: nodeId,
          label: conn.relation,
          arrows: 'to',
          color: {{ color: '#3498db' }},
          font: {{ size: 10, color: '#666' }}
        }});
      }});
      
      // Add outgoing nodes (green)
      connections.outgoing.forEach(conn => {{
        const tgtNode = nodeIndex.nodes[conn.target];
        if (tgtNode && !addedNodes.has(conn.target)) {{
          nodes.push({{
            id: conn.target,
            label: tgtNode.label || conn.target,
            color: {{ background: '#2ecc71', border: '#27ae60' }},
            size: 20,
            font: {{ size: 14, color: '#fff', face: 'Segoe UI' }}
          }});
          addedNodes.add(conn.target);
        }}
        edges.push({{
          from: nodeId,
          to: conn.target,
          label: conn.relation,
          arrows: 'to',
          color: {{ color: '#2ecc71' }},
          font: {{ size: 10, color: '#666' }}
        }});
      }});
      
      // Update info bar
      document.getElementById('info-bar').innerHTML = `
        <strong>${{centerNode.label || nodeId}}</strong> •
        ${{connections.incoming.length}} incoming •
        ${{connections.outgoing.length}} outgoing •
        ${{connections.neighbors.length}} total connections
      `;
      
      // Create or update network
      const container = document.getElementById('graph');
      const data = {{ nodes: nodes, edges: edges }};
      const options = {{
        physics: {{
          enabled: true,
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {{
            gravitationalConstant: -150,
            centralGravity: 0.005,
            springLength: 350,
            springConstant: 0.02,
            damping: 0.4
          }},
          stabilization: {{
            iterations: 200,
            updateInterval: 25
          }}
        }},
        interaction: {{
          hover: true,
          tooltipDelay: 100,
          dragNodes: true,
          dragView: true,
          zoomView: true
        }},
        nodes: {{
          shape: 'dot',
          borderWidth: 3,
          shadow: true
        }},
        edges: {{
          width: 2,
          smooth: {{
            type: 'continuous',
            roundness: 0.5
          }}
        }}
      }};
      
      if (network) {{
        network.setData(data);
      }} else {{
        network = new vis.Network(container, data, options);
        
        // Click on node to select it
        network.on('click', (params) => {{
          if (params.nodes.length > 0) {{
            const clickedNodeId = params.nodes[0];
            if (clickedNodeId !== currentNodeId) {{
              selectNode(clickedNodeId);
            }}
          }}
        }});
      }}
    }}
  </script>
</body>
</html>
"""


def emit_focused_graph_html(
    graph: Dict[str, Any],
    node_index: Dict[str, Any],
    *,
    title: str,
    header: str,
) -> str:
    """Generate HTML for focused graph view."""
    graph_json = json.dumps(graph, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    index_json = json.dumps(node_index, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    
    return _HTML_TEMPLATE.format(
        title=_html.escape(title),
        header=_html.escape(header),
        graph_data=graph_json,
        node_index=index_json,
    )


def write_focused_graph_html(
    graph_path: Path,
    output_path: Path,
    *,
    project_label: str | None = None,
) -> Path:
    """Write focused graph HTML."""
    from graphify.security import check_graph_file_size_cap
    check_graph_file_size_cap(graph_path)
    
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    node_index = build_node_index(graph)
    
    project_name = project_label or "Project"
    title = f"{project_name} — Focused Graph View"
    header = f"{project_name} — Interactive Graph (One Node at a Time)"
    
    html = emit_focused_graph_html(graph, node_index, title=title, header=header)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path

# Made with Bob
