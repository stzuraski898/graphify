"""Enhanced tree view with call relationship analysis.

When clicking on a class/file, shows:
- Incoming calls: Who calls this class's functions
- Outgoing calls: Which external functions this class calls
"""
from __future__ import annotations

import html as _html
import json
from pathlib import Path
from typing import Any, Dict

from graphify.tree_html import build_tree


def build_call_relationships(graph: Dict[str, Any]) -> Dict[str, Dict]:
    """Build a lookup of call relationships for each node.
    
    Returns:
        Dict mapping node_id to {
            'incoming': [(caller_id, caller_label, relation)],
            'outgoing': [(callee_id, callee_label, relation)]
        }
    """
    nodes_by_id = {n['id']: n for n in graph.get('nodes', [])}
    relationships = {}
    
    for edge in graph.get('edges', []):
        src = edge.get('source')
        tgt = edge.get('target')
        rel = edge.get('relation', 'unknown')
        
        if not src or not tgt:
            continue
            
        # Skip stdlib nodes
        if src.startswith('stdlib_') or tgt.startswith('stdlib_'):
            continue
        
        # Add outgoing edge for source
        if src not in relationships:
            relationships[src] = {'incoming': [], 'outgoing': []}
        src_node = nodes_by_id.get(tgt, {})
        relationships[src]['outgoing'].append({
            'id': tgt,
            'label': src_node.get('label', tgt),
            'relation': rel,
            'file': src_node.get('source_file', '')
        })
        
        # Add incoming edge for target
        if tgt not in relationships:
            relationships[tgt] = {'incoming': [], 'outgoing': []}
        tgt_node = nodes_by_id.get(src, {})
        relationships[tgt]['incoming'].append({
            'id': src,
            'label': tgt_node.get('label', src),
            'relation': rel,
            'file': tgt_node.get('source_file', '')
        })
    
    return relationships


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
      background: #f9f9f9;
      color: #333;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }}
    h1 {{
      margin: 20px 0 0 24px;
      font-size: 2.2rem;
      font-weight: bold;
      color: #1e3a56;
    }}
    .controls {{
      margin: 20px 0 15px 24px;
    }}
    button {{
      margin-right: 10px;
      padding: 8px 18px;
      background: #007bff;
      color: #fff;
      border: none;
      border-radius: 5px;
      font-size: 0.95rem;
      cursor: pointer;
      transition: background 0.2s ease-in-out;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    button:hover {{
      background: #0056b3;
    }}
    button:active {{
      background: #004085;
    }}
    .main-container {{
      display: flex;
      flex: 1;
      gap: 20px;
      padding: 0 24px 24px 24px;
      overflow: hidden;
    }}
    #tree-container {{
      flex: 1;
      overflow: auto;
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      border: 1px solid #ddd;
    }}
    #details-panel {{
      width: 400px;
      overflow: auto;
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      border: 1px solid #ddd;
      padding: 20px;
      display: none;
    }}
    #details-panel.visible {{
      display: block;
    }}
    #details-panel h2 {{
      margin: 0 0 15px 0;
      font-size: 1.5rem;
      color: #1e3a56;
      border-bottom: 2px solid #007bff;
      padding-bottom: 10px;
    }}
    #details-panel h3 {{
      margin: 20px 0 10px 0;
      font-size: 1.2rem;
      color: #333;
    }}
    #details-panel .section {{
      margin-bottom: 25px;
    }}
    #details-panel .call-list {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    #details-panel .call-item {{
      padding: 8px 12px;
      margin: 5px 0;
      background: #f8f9fa;
      border-left: 3px solid #007bff;
      border-radius: 4px;
      font-size: 0.9rem;
    }}
    #details-panel .call-item.incoming {{
      border-left-color: #28a745;
    }}
    #details-panel .call-item.outgoing {{
      border-left-color: #dc3545;
    }}
    #details-panel .call-label {{
      font-weight: 600;
      color: #1a1a1a;
    }}
    #details-panel .call-relation {{
      color: #666;
      font-size: 0.85rem;
      font-style: italic;
    }}
    #details-panel .call-file {{
      color: #888;
      font-size: 0.8rem;
      margin-top: 3px;
    }}
    #details-panel .empty {{
      color: #999;
      font-style: italic;
      padding: 10px;
    }}
    #details-panel .close-btn {{
      float: right;
      background: #dc3545;
      padding: 5px 12px;
      font-size: 0.85rem;
    }}
    #details-panel .close-btn:hover {{
      background: #c82333;
    }}
    svg {{
      background: #fff;
      border-radius: 8px;
      display: block;
    }}
    .node circle {{
      stroke-width: 2.5px;
      cursor: pointer;
    }}
    .node.selected circle {{
      stroke-width: 4px;
      stroke: #007bff !important;
    }}
    .node text {{
      font: 18px 'Segoe UI', sans-serif;
      font-weight: 600;
      paint-order: stroke fill;
      stroke: #fff;
      stroke-width: 5px;
      stroke-linejoin: round;
      stroke-opacity: 0.95;
      pointer-events: none;
    }}
    .node text tspan {{
      fill: #1a1a1a;
    }}
    .node-count {{
      font-size: 13px;
      font-weight: 400;
      fill: #666 !important;
    }}
    .link {{
      fill: none;
      stroke-opacity: 0.7;
      stroke-width: 2px;
    }}
  </style>
</head>
<body>
  <h1>{header}</h1>
  <div class="controls">
    <button onclick="expandAll()">Expand All</button>
    <button onclick="collapseAll()">Collapse All</button>
    <button onclick="resetView()">Reset View</button>
    <button onclick="closeDetails()">Close Details</button>
  </div>
  <div class="main-container">
    <div id="tree-container">
      <svg id="tree-svg" width="{svg_width}" height="{svg_height}"></svg>
    </div>
    <div id="details-panel">
      <button class="close-btn" onclick="closeDetails()">×</button>
      <h2 id="details-title">Select a node</h2>
      <div class="section">
        <h3>📥 Incoming Calls (<span id="incoming-count">0</span>)</h3>
        <div id="incoming-calls" class="call-list"></div>
      </div>
      <div class="section">
        <h3>📤 Outgoing Calls (<span id="outgoing-count">0</span>)</h3>
        <div id="outgoing-calls" class="call-list"></div>
      </div>
    </div>
  </div>

  <script src="https://d3js.org/d3.v7.min.js"></script>
  <script>
    const initialJsonData = {data_json};
    const callRelationships = {call_relationships};
    let selectedNodeId = null;

    function transformData(jsonData) {{
      function processNode(node, parentL1StageName) {{
        let displayName = node.name;
        displayName = displayName.replace(/\.(cc|cpp|h|hpp|c|py|js|ts)$/i, '');
        
        const newNode = {{ 
          name: displayName,
          count: node.total_count,
          originalName: node.name,
          nodeId: node.id || displayName.toLowerCase().replace(/\s+/g, '_')
        }};

        if (parentL1StageName === "Root") {{
          newNode.originalStageName = node.name;
        }} else {{
          newNode.originalStageName = parentL1StageName;
        }}

        if (node.children && node.children.length > 0) {{
          const stageNameToPass = (parentL1StageName === "Root") ? node.name : parentL1StageName;
          newNode.children = node.children.map(child => processNode(child, stageNameToPass));
        }}

        return newNode;
      }}

      return {{
        name: jsonData.name,
        count: jsonData.total_count,
        originalStageName: "Root",
        children: (jsonData.children || []).map(child => processNode(child, "Root"))
      }};
    }}

    const treeData = transformData(initialJsonData);

    // [Rest of D3 tree code - same as before but with click handler]
    const svgElement = d3.select("#tree-svg");
    const initialSvgWidth = +svgElement.attr("width");
    const initialSvgHeight = +svgElement.attr("height");
    const margin = {{ top: 40, right: 120, bottom: 80, left: 500 }};
    let width = initialSvgWidth - margin.left - margin.right;
    let height = initialSvgHeight - margin.top - margin.bottom;
    const duration = 500;
    let nodeCounter = 0;
    const g = svgElement.append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);
    const treemap = d3.tree().nodeSize([50, 0]);
    let rootNode = d3.hierarchy(treeData, d => d.children);
    rootNode.x0 = 0;
    rootNode.y0 = 0;

    if (rootNode.children) {{
      rootNode.children.forEach(d_child => {{
        if (d_child.children) {{ collapseBranch(d_child); }}
      }});
    }}
    updateTree(rootNode);

    function collapseBranch(d) {{ if (d.children) {{ d._children = d.children; d._children.forEach(collapseBranch); d.children = null; }} }}
    function expandBranch(d) {{ if (d._children) {{ d.children = d._children; d._children = null; }} if (d.children) {{ d.children.forEach(expandBranch); }} }}
    window.expandAll = () => {{ expandBranch(rootNode); updateTree(rootNode); }};
    window.collapseAll = () => {{ if (rootNode.children) {{ rootNode.children.forEach(collapseBranch); }} updateTree(rootNode); }};
    window.resetView = () => {{ if (rootNode.children) {{ rootNode.children.forEach(d_child => {{ if (d_child.children || d_child._children) {{ collapseBranch(d_child); }} }}); }} if (rootNode._children && !rootNode.children) {{ rootNode.children = rootNode._children; rootNode._children = null; }} updateTree(rootNode); }};
    
    window.closeDetails = () => {{
      document.getElementById('details-panel').classList.remove('visible');
      d3.selectAll('.node').classed('selected', false);
      selectedNodeId = null;
    }};

    function showNodeDetails(nodeData) {{
      const nodeName = nodeData.data.originalName || nodeData.data.name;
      const nodeId = nodeData.data.nodeId;
      
      selectedNodeId = nodeId;
      d3.selectAll('.node').classed('selected', false);
      d3.select(nodeData).classed('selected', true);
      
      document.getElementById('details-title').textContent = nodeName;
      
      const rels = callRelationships[nodeId] || {{ incoming: [], outgoing: [] }};
      
      // Incoming calls
      const incomingDiv = document.getElementById('incoming-calls');
      document.getElementById('incoming-count').textContent = rels.incoming.length;
      if (rels.incoming.length === 0) {{
        incomingDiv.innerHTML = '<div class="empty">No incoming calls</div>';
      }} else {{
        incomingDiv.innerHTML = rels.incoming.map(call => `
          <div class="call-item incoming">
            <div class="call-label">${{call.label}}</div>
            <div class="call-relation">${{call.relation}}</div>
            ${{call.file ? `<div class="call-file">${{call.file}}</div>` : ''}}
          </div>
        `).join('');
      }}
      
      // Outgoing calls
      const outgoingDiv = document.getElementById('outgoing-calls');
      document.getElementById('outgoing-count').textContent = rels.outgoing.length;
      if (rels.outgoing.length === 0) {{
        outgoingDiv.innerHTML = '<div class="empty">No outgoing calls</div>';
      }} else {{
        outgoingDiv.innerHTML = rels.outgoing.map(call => `
          <div class="call-item outgoing">
            <div class="call-label">${{call.label}}</div>
            <div class="call-relation">${{call.relation}}</div>
            ${{call.file ? `<div class="call-file">${{call.file}}</div>` : ''}}
          </div>
        `).join('');
      }}
      
      document.getElementById('details-panel').classList.add('visible');
    }}

    function updateTree(source) {{
      const treeLayoutData = treemap(rootNode);
      let nodes = treeLayoutData.descendants();
      let links = treeLayoutData.descendants().slice(1);

      let minX = 0, maxX = 0;
      if (nodes.length > 0) {{
        minX = d3.min(nodes, d => d.x);
        maxX = d3.max(nodes, d => d.x);
      }}

      let neededHeight = Math.max(initialSvgHeight, maxX - minX + margin.top + margin.bottom + 100);
      svgElement.transition().duration(duration / 2).attr("height", neededHeight);
      g.transition().duration(duration / 2).attr("transform", `translate(${{margin.left}},${{margin.top - minX + 40}})`);

      nodes.forEach(d => {{ d.y = d.depth * 450; }});

      const node = g.selectAll('g.node').data(nodes, d => d.id || (d.id = ++nodeCounter));
      const nodeEnter = node.enter().append('g')
        .attr('class', d => "node" + (d.children || d._children ? " node--internal" : " node--leaf") + (d._children ? " _children" : ""))
        .attr('transform', d => `translate(${{source.y0}},${{source.x0}})`)
        .on('click', (event, d) => {{
          if (event.shiftKey || event.ctrlKey) {{
            // Show details on Shift+Click or Ctrl+Click
            showNodeDetails(d);
          }} else {{
            // Toggle expand/collapse on regular click
            if (d.children) {{ d._children = d.children; d.children = null; }} 
            else if (d._children) {{ d.children = d._children; d._children = null; }}
            updateTree(d);
          }}
        }})
        .style('cursor', 'pointer');

      nodeEnter.append('circle').attr('r', 1e-6);

      nodeEnter.append('text')
        .attr('dy', '.35em')
        .attr('x', d => d.children || d._children ? -16 : 16)
        .attr('text-anchor', d => d.children || d._children ? 'end' : 'start')
        .style("fill-opacity", 1e-6)
        .call(wrapText, 420);

      const nodeUpdate = nodeEnter.merge(node);
      nodeUpdate.transition().duration(duration)
        .attr('transform', d => `translate(${{d.y}},${{d.x}})`)
        .attr('class', d => "node" + (d.children ? " node--internal" : " node--leaf") + (d._children ? " node--internal _children" : ""));

      nodeUpdate.select('circle').attr('r', 10)
        .style('fill', d => {{
          if (d._children) return "#a3d391";
          if (d.children) return "#6ab04c";
          return "#fff";
        }})
        .style('stroke', d => "#508a38");
      
      nodeUpdate.select('text').style("fill-opacity", 1).call(wrapText, 420);

      const nodeExit = node.exit().transition().duration(duration).attr('transform', d => `translate(${{source.y}},${{source.x}})`).remove();
      nodeExit.select('circle').attr('r', 1e-6);
      nodeExit.select('text').style('fill-opacity', 1e-6);

      const link = g.selectAll('path.link').data(links, d => d.id);
      const linkEnter = link.enter().insert('path', "g").attr('class', 'link').attr('d', d => {{ const o = {{ x: source.x0, y: source.y0 }}; return diagonal(o, o); }});

      linkEnter.merge(link).transition().duration(duration).attr('d', d => diagonal(d, d.parent))
        .style('stroke', "#508a38");
      link.exit().transition().duration(duration).attr('d', d => {{ const o = {{ x: source.x, y: source.y }}; return diagonal(o, o); }}).remove();
      nodes.forEach(d => {{ d.x0 = d.x; d.y0 = d.y; }});
    }}

    function diagonal(s, d) {{ return `M ${{s.y}} ${{s.x}} C ${{(s.y + d.y) / 2}} ${{s.x}}, ${{(s.y + d.y) / 2}} ${{d.x}}, ${{d.y}} ${{d.x}}`; }}

    function wrapText(textElements, maxWidth) {{
      textElements.each(function () {{
        const textD3 = d3.select(this);
        const nodeData = textD3.datum().data;
        const originalNodeText = nodeData.name;
        const count = nodeData.count;
        const x = parseFloat(textD3.attr("x") || 0);
        const initialDy = textD3.attr("dy");
        const textAnchor = textD3.attr("text-anchor");
        const lineHeight = 1.1;

        textD3.text(null);

        const words = originalNodeText.split(/\s+/).filter(Boolean);
        let currentTspan = textD3.append("tspan")
          .attr("x", x)
          .attr("dy", initialDy);
        if (textAnchor === "end") currentTspan.attr("text-anchor", "end");

        let currentLine = [];
        
        for (let i = 0; i < words.length; i++) {{
          currentLine.push(words[i]);
          currentTspan.text(currentLine.join(" "));

          if (currentTspan.node().getComputedTextLength() > maxWidth && currentLine.length > 1) {{
            currentLine.pop();
            currentTspan.text(currentLine.join(" "));
            
            currentLine = [words[i]];
            currentTspan = textD3.append("tspan")
              .attr("x", x)
              .attr("dy", lineHeight + "em")
              .text(words[i]);
            if (textAnchor === "end") currentTspan.attr("text-anchor", "end");
          }}
        }}

        if (count !== undefined && count > 0) {{
          textD3.append("tspan")
            .attr("x", x)
            .attr("dy", lineHeight + "em")
            .attr("class", "node-count")
            .text(`(${{count}})`);
        }}
      }});
    }}
  </script>
</body>
</html>
"""


def emit_html_with_calls(
    tree: Dict[str, Any],
    graph: Dict[str, Any],
    *,
    title: str,
    header: str,
    svg_width: int = 6000,
    svg_height: int = 8000,
) -> str:
    """Generate HTML with tree view and call relationship panel."""
    # Build call relationships
    call_rels = build_call_relationships(graph)
    
    # Escape data for JavaScript
    data_json = json.dumps(tree, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    call_rels_json = json.dumps(call_rels, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    
    return _HTML_TEMPLATE.format(
        title=_html.escape(title),
        header=_html.escape(header),
        svg_width=svg_width,
        svg_height=svg_height,
        data_json=data_json,
        call_relationships=call_rels_json,
    )


def write_tree_with_calls_html(
    graph_path: Path,
    output_path: Path,
    *,
    root: str | None = None,
    max_children: int = 200,
    project_label: str | None = None,
) -> Path:
    """Write enhanced tree HTML with call relationships."""
    from graphify.security import check_graph_file_size_cap
    check_graph_file_size_cap(graph_path)
    
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    tree = build_tree(graph, root=root, max_children=max_children,
                      project_label=project_label)
    title = f"{tree['name']} — graphify tree with calls"
    header = f"{tree['name']} — Knowledge Graph (Click nodes to see calls)"
    html = emit_html_with_calls(tree, graph, title=title, header=header)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path

# Made with Bob
