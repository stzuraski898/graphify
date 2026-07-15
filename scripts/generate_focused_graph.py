#!/usr/bin/env python3
"""Generate focused graph view from graphify output.

This script creates an interactive force-directed graph visualization that shows
one node and its connections at a time, making it easy to explore large codebases
without visual clutter.

Usage:
    python scripts/generate_focused_graph.py [OPTIONS]

Examples:
    # Generate from default location
    python scripts/generate_focused_graph.py

    # Specify custom paths
    python scripts/generate_focused_graph.py --graph path/to/graph.json --output path/to/output.html

    # Use deduplicated graph
    python scripts/generate_focused_graph.py --graph graphify-out/graph-dedup.json
"""
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphify.focused_graph_html import write_focused_graph_html


def main():
    parser = argparse.ArgumentParser(
        description='Generate focused graph view from graphify output',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from default location
  %(prog)s

  # Specify custom graph file
  %(prog)s --graph path/to/graph.json

  # Use deduplicated graph
  %(prog)s --graph graphify-out/graph-dedup.json --output graphify-out/focused.html

  # Custom project name
  %(prog)s --project "My Project"

Features:
  - Shows one node and its connections at a time
  - Search for any class or file
  - Color-coded: red (selected), blue (incoming), green (outgoing)
  - Draggable nodes - arrange them however you like
  - Zoom and pan controls
  - Dark background for better contrast
        """
    )
    
    parser.add_argument(
        '--graph',
        type=Path,
        default=Path('graphify-out/graph.json'),
        help='Path to graph.json file (default: graphify-out/graph.json)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        help='Output HTML file path (default: same directory as graph, named *-focused.html)'
    )
    
    parser.add_argument(
        '--project',
        type=str,
        help='Project name for the title (default: derived from graph path)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed progress information'
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not args.graph.exists():
        print(f"Error: Graph file not found: {args.graph}", file=sys.stderr)
        print(f"Run 'graphify build' first to generate the graph.", file=sys.stderr)
        return 1
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Default: same directory as graph, with -focused suffix
        graph_stem = args.graph.stem.replace('.json', '')
        output_path = args.graph.parent / f"{graph_stem}-focused.html"
    
    # Determine project name
    if args.project:
        project_name = args.project
    else:
        # Try to derive from path
        if 'dedup' in str(args.graph):
            project_name = f"{args.graph.parent.parent.name} (Deduplicated)"
        else:
            project_name = args.graph.parent.parent.name
    
    if args.verbose:
        print(f"Input graph: {args.graph}")
        print(f"Output HTML: {output_path}")
        print(f"Project name: {project_name}")
        print()
    
    # Generate the focused graph
    try:
        print(f"Generating focused graph view...")
        result_path = write_focused_graph_html(
            args.graph,
            output_path,
            project_label=project_name
        )
        print(f"✓ Generated: {result_path}")
        print()
        print("Open in browser:")
        print(f"  firefox {result_path} &")
        print()
        print("Features:")
        print("  - Search for any class or file")
        print("  - Click nodes to focus on them")
        print("  - Drag nodes to rearrange")
        print("  - Zoom with mouse wheel")
        print("  - Pan by dragging empty space")
        return 0
        
    except Exception as e:
        print(f"Error generating focused graph: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
