#!/usr/bin/env python3
"""Generate a 2-degree focused graph view from graph.json.

Shows:
- Center: Selected class
- 1st degree: Methods of that class (orange)
- 2nd degree: External callers (blue) and callees (green)
"""
import argparse
import sys
from pathlib import Path

# Add parent directory to path to import graphify
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphify.focused_graph_2deg_html import write_focused_graph_2deg_html


def main():
    parser = argparse.ArgumentParser(
        description="Generate 2-degree focused graph view",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From default location
  python scripts/generate_focused_graph_2deg.py

  # From deduplicated graph
  python scripts/generate_focused_graph_2deg.py --graph graphify-out/graph-dedup.json

  # Custom paths
  python scripts/generate_focused_graph_2deg.py \\
    --graph path/to/graph.json \\
    --output path/to/output.html \\
    --project "My Project"
        """
    )
    
    parser.add_argument(
        '--graph',
        default='graphify-out/graph.json',
        help='Path to graph.json file (default: graphify-out/graph.json)'
    )
    
    parser.add_argument(
        '--output',
        help='Output HTML file path (default: same dir as graph, with -focused-2deg.html suffix)'
    )
    
    parser.add_argument(
        '--project',
        default='Project',
        help='Project name for the title (default: "Project")'
    )
    
    args = parser.parse_args()
    
    graph_path = Path(args.graph).expanduser()
    
    if not graph_path.exists():
        print(f"Error: Graph file not found: {graph_path}", file=sys.stderr)
        return 1
    
    # Determine output path
    if args.output:
        output_path = Path(args.output).expanduser()
    else:
        # Default: same directory as graph, with -focused-2deg.html suffix
        output_path = graph_path.parent / graph_path.name.replace('.json', '-focused-2deg.html')
    
    print("Generating 2-degree focused graph view...")
    write_focused_graph_2deg_html(graph_path, output_path, args.project)
    
    print(f"✓ Generated: {output_path}")
    print()
    print("Open in browser:")
    print(f"  firefox {output_path} &")
    print()
    print("Features:")
    print("  - Search for any class")
    print("  - See class methods (orange, 1st degree)")
    print("  - See external callers (blue, 2nd degree)")
    print("  - See external callees (green, 2nd degree)")
    print("  - Click nodes to explore other classes")
    print("  - Drag nodes to rearrange")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
