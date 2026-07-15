"""Focused graph view with 2-degree separation - shows class, its methods, and external callers.

Shows:
1. Center: Selected class/node
2. First degree: Methods/functions of that class
3. Second degree: External nodes that call those methods
"""
from __future__ import annotations

import html as _html
import json
from pathlib import Path
from typing import Any, Dict, Set


def extract_class_from_id(node_id: str) -> str:
    """Extract class name from node ID like 'activepymodule_activepymodule_load' -> 'activepymodule'."""
    parts = node_id.split('_')
    if len(parts) >= 2:
        return parts[0]  # First part is usually the file/class
    return node_id


def build_node_index(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Build searchable index of nodes with their connections."""
    nodes_by_id = {n['id']: n for n in graph.get('nodes', [])}
    
    # Build adjacency lists
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
    
    # Group nodes by class/file for easier selection
    classes = {}
    for node_id, data in node_connections.items():
        if node_id.startswith('stdlib_'):
            continue
        class_name = extract_class_from_id(node_id)
        if class_name not in classes:
            classes[class_name] = {
                'name': class_name,
                'methods': [],
                'total_connections': 0
            }
        classes[class_name]['methods'].append(node_id)
        classes[class_name]['total_connections'] += len(data['neighbors'])
    
    # Convert to list and sort by connections
    class_list = []
    for class_name, data in classes.items():
        class_list.append({
            'id': class_name,
            'label': class_name,
            'method_count': len(data['methods']),
            'total_connections': data['total_connections']
        })
    
    class_list.sort(key=lambda x: x['total_connections'], reverse=True)
    
    return {
        'nodes': nodes_by_id,
        'connections': node_connections,
        'classes': classes,
        'class_list': class_list
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
      margin: 0 0 16px 0;
      font-size: 24px;
      color: #2c3e50;
    }}
    .controls {{
      display: flex;
      gap: 16px;
      align-items: flex-start;
    }}
    .node-selector {{
      flex: 1;
      position: relative;
    }}
    #node-search {{
      width: 100%;
      padding: 12px 16px;
      font-size: 14px;
      border: 2px solid #ddd;
      border-radius: 6px;
      box-sizing: border-box;
    }}
    #node-search:focus {{
      outline: none;
      border-color: #3498db;
    }}
    .suggestions {{
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: white;
      border: 2px solid #3498db;
      border-top: none;
      border-radius: 0 0 6px 6px;
      max-height: 400px;
      overflow-y: auto;
      display: none;
      z-index: 1000;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .suggestions.visible {{
      display: block;
    }}
    .suggestion-item {{
      padding: 12px 16px;
      cursor: pointer;
      border-bottom: 1px solid #eee;
    }}
    .suggestion-item:hover {{
      background: #f8f9fa;
    }}
    .suggestion-label {{
      font-weight: 600;
      color: #2c3e50;
      margin-bottom: 4px;
    }}
    .suggestion-meta {{
      font-size: 12px;
      color: #7f8c8d;
    }}
    .info-bar {{
      flex: 1;
      padding: 12px 16px;
      background: #ecf0f1;
      border-radius: 6px;
      font-size: 14px;
      color: #2c3e50;
    }}
    #graph-container {{
      flex: 1;
      position: relative;
      overflow: hidden;
    }}
    #graph {{
      width: 100%;
      height: 100%;
    }}
    .legend {{
      position: absolute;
      top: 20px;
      right: 20px;
      background: rgba(255, 255, 255, 0.95);
      padding: 16px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      font-size: 13px;
    }}
    .legend-title {{
      font-weight: 600;
      margin-bottom: 12px;
      color: #2c3e50;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      margin-bottom: 8px;
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
          placeholder="Search for a class (e.g., DaemonServer, ActivePyModule)..."
          autocomplete="off"
        />
        <div id="suggestions" class="suggestions"></div>
      </div>
      <div class="info-bar" id="info-bar">
        Select a class to see its methods and callers
      </div>
    </div>
  </div>
  <div id="graph-container">
    <div id="graph"></div>
    <div class="legend">
      <div class="legend-title">Legend</div>
      <div class="legend-item">
        <div class="legend-color" style="background: #e74c3c; border-color: #c0392b;"></div>
        <span>Selected Class</span>
      </div>
      <div class="legend-item">
        <div class="legend-color" style="background: #f39c12; border-color: #d68910;"></div>
        <span>Methods (1st degree)</span>
      </div>
      <div class="legend-item">
        <div class="legend-color" style="background: #3498db; border-color: #2980b9;"></div>
        <span>External Callers (2nd degree)</span>
      </div>
      <div class="legend-item">
        <div class="legend-color" style="background: #2ecc71; border-color: #27ae60;"></div>
        <span>Called By Methods (2nd degree)</span>
      </div>
    </div>
  </div>

  <script src="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js"></script>
  <script>
    const graphData = {graph_data};
    const nodeIndex = {node_index};
    
    let network = null;
    let currentClassId = null;
    
    // Initialize with most connected class
    if (nodeIndex.class_list.length > 0) {{
      currentClassId = nodeIndex.class_list[0].id;
      updateGraph(currentClassId);
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
      
      const matches = nodeIndex.class_list.filter(c => 
        c.label.toLowerCase().includes(query)
      ).slice(0, 10);
      
      if (matches.length === 0) {{
        suggestionsDiv.classList.remove('visible');
        return;
      }}
      
      suggestionsDiv.innerHTML = matches.map(c => `
        <div class="suggestion-item" data-class-id="${{c.id}}">
          <div class="suggestion-label">${{c.label}}</div>
          <div class="suggestion-meta">
            ${{c.method_count}} methods • ${{c.total_connections}} total connections
          </div>
        </div>
      `).join('');
      
      suggestionsDiv.classList.add('visible');
      
      // Add click handlers
      suggestionsDiv.querySelectorAll('.suggestion-item').forEach(item => {{
        item.addEventListener('click', () => {{
          const classId = item.getAttribute('data-class-id');
          selectClass(classId);
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
    
    function selectClass(classId) {{
      currentClassId = classId;
      updateGraph(classId);
    }}
    
    function updateGraph(classId) {{
      const classData = nodeIndex.classes[classId];
      if (!classData) {{
        console.error('Class not found:', classId);
        return;
      }}
      
      const nodes = [];
      const edges = [];
      const addedNodes = new Set();
      
      // Add center node (virtual class node)
      const centerNodeId = `class_${{classId}}`;
      nodes.push({{
        id: centerNodeId,
        label: classId,
        color: {{ background: '#e74c3c', border: '#c0392b' }},
        size: 35,
        font: {{ size: 20, color: '#fff', face: 'Segoe UI', bold: true }},
        shape: 'box'
      }});
      addedNodes.add(centerNodeId);
      
      // Track external callers and callees
      const externalCallers = new Map(); // who calls our methods
      const externalCallees = new Map(); // who our methods call
      
      // Add methods (1st degree - orange)
      classData.methods.forEach(methodId => {{
        const methodNode = nodeIndex.nodes[methodId];
        if (!methodNode) return;
        
        nodes.push({{
          id: methodId,
          label: methodNode.label || methodId.split('_').pop(),
          color: {{ background: '#f39c12', border: '#d68910' }},
          size: 25,
          font: {{ size: 16, color: '#fff', face: 'Segoe UI', bold: true }}
        }});
        addedNodes.add(methodId);
        
        // Connect method to class
        edges.push({{
          from: centerNodeId,
          to: methodId,
          color: {{ color: '#e74c3c' }},
          width: 3,
          arrows: 'to'
        }});
        
        // Find external callers (2nd degree - blue)
        const connections = nodeIndex.connections[methodId];
        if (connections) {{
          connections.incoming.forEach(conn => {{
            const callerClass = extract_class_from_id(conn.source);
            if (callerClass !== classId) {{
              if (!externalCallers.has(conn.source)) {{
                externalCallers.set(conn.source, []);
              }}
              externalCallers.get(conn.source).push({{
                method: methodId,
                relation: conn.relation
              }});
            }}
          }});
          
          // Find external callees (2nd degree - green)
          connections.outgoing.forEach(conn => {{
            const calleeClass = extract_class_from_id(conn.target);
            if (calleeClass !== classId) {{
              if (!externalCallees.has(conn.target)) {{
                externalCallees.set(conn.target, []);
              }}
              externalCallees.get(conn.target).push({{
                method: methodId,
                relation: conn.relation
              }});
            }}
          }});
        }}
      }});
      
      // Add external callers (blue)
      externalCallers.forEach((calls, callerId) => {{
        const callerNode = nodeIndex.nodes[callerId];
        if (callerNode && !addedNodes.has(callerId)) {{
          nodes.push({{
            id: callerId,
            label: callerNode.label || callerId.split('_').pop(),
            color: {{ background: '#3498db', border: '#2980b9' }},
            size: 20,
            font: {{ size: 14, color: '#fff', face: 'Segoe UI' }}
          }});
          addedNodes.add(callerId);
        }}
        
        // Connect caller to the specific method it calls
        calls.forEach(call => {{
          edges.push({{
            from: callerId,
            to: call.method,
            label: call.relation,
            color: {{ color: '#3498db' }},
            width: 2,
            arrows: 'to',
            font: {{ size: 10, color: '#666' }}
          }});
        }});
      }});
      
      // Add external callees (green)
      externalCallees.forEach((calls, calleeId) => {{
        const calleeNode = nodeIndex.nodes[calleeId];
        if (calleeNode && !addedNodes.has(calleeId)) {{
          nodes.push({{
            id: calleeId,
            label: calleeNode.label || calleeId.split('_').pop(),
            color: {{ background: '#2ecc71', border: '#27ae60' }},
            size: 20,
            font: {{ size: 14, color: '#fff', face: 'Segoe UI' }}
          }});
          addedNodes.add(calleeId);
        }}
        
        // Connect method to what it calls
        calls.forEach(call => {{
          edges.push({{
            from: call.method,
            to: calleeId,
            label: call.relation,
            color: {{ color: '#2ecc71' }},
            width: 2,
            arrows: 'to',
            font: {{ size: 10, color: '#666' }}
          }});
        }});
      }});
      
      // Update info bar
      document.getElementById('info-bar').innerHTML = `
        <strong>${{classId}}</strong> • 
        ${{classData.methods.length}} methods • 
        ${{externalCallers.size}} external callers • 
        ${{externalCallees.size}} external callees
      `;
      
      // Create or update network
      const container = document.getElementById('graph');
      const data = {{ nodes: nodes, edges: edges }};
      const options = {{
        physics: {{
          enabled: true,
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {{
            gravitationalConstant: -200,
            centralGravity: 0.01,
            springLength: 250,
            springConstant: 0.02,
            damping: 0.4
          }},
          stabilization: {{
            iterations: 300,
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
          borderWidth: 3,
          shadow: true
        }},
        edges: {{
          smooth: {{
            type: 'continuous',
            roundness: 0.5
          }}
        }},
        layout: {{
          hierarchical: {{
            enabled: false
          }}
        }}
      }};
      
      if (network) {{
        network.setData(data);
      }} else {{
        network = new vis.Network(container, data, options);
        
        // Click on node to select it (if it's a method, select its class)
        network.on('click', (params) => {{
          if (params.nodes.length > 0) {{
            const clickedNodeId = params.nodes[0];
            if (clickedNodeId.startsWith('class_')) {{
              return; // Already selected
            }}
            const clickedClass = extract_class_from_id(clickedNodeId);
            if (clickedClass && clickedClass !== classId) {{
              selectClass(clickedClass);
            }}
          }}
        }});
      }}
    }}
    
    function extract_class_from_id(nodeId) {{
      const parts = nodeId.split('_');
      if (parts.length >= 2) {{
        return parts[0];
      }}
      return nodeId;
    }}
  </script>
</body>
</html>
"""


def write_focused_graph_2deg_html(
    graph_path: str | Path,
    output_path: str | Path,
    project_label: str = "Project"
) -> None:
    """Generate 2-degree focused graph HTML."""
    graph_path = Path(graph_path)
    output_path = Path(output_path)
    
    with open(graph_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)
    
    node_index = build_node_index(graph)
    
    html_content = _HTML_TEMPLATE.format(
        title=f"{project_label} — Interactive Graph (2-Degree View)",
        header=f"{project_label} — Interactive Graph (One Class at a Time)",
        graph_data=json.dumps(graph),
        node_index=json.dumps(node_index)
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

# Made with Bob
