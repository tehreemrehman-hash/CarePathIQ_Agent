"""Test Phase 4 visualization generation"""
import sys
from streamlit_app import build_graphviz_from_nodes, render_graphviz_bytes
import base64

# Test with sample nodes
test_nodes = [
    {
        'id': '1',
        'label': 'Start',
        'type': 'start',
        'next': '2'
    },
    {
        'id': '2', 
        'label': 'Question',
        'type': 'question',
        'next': '3',
        'options': ['Yes', 'No']
    },
    {
        'id': '3',
        'label': 'End',
        'type': 'end'
    }
]

print("Testing Phase 4 visualization generation...")
print("=" * 60)

# Test build_graphviz_from_nodes
print("\n1. Building graphviz object...")
try:
    graph = build_graphviz_from_nodes(test_nodes)
    print(f"   Graph object type: {type(graph)}")
    print(f"   Graph is None: {graph is None}")
    if graph:
        print(f"   Graph source preview (first 200 chars):\n{str(graph.source)[:200]}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test render_graphviz_bytes
print("\n2. Rendering SVG bytes...")
try:
    svg_bytes = render_graphviz_bytes(graph)
    print(f"   SVG bytes type: {type(svg_bytes)}")
    print(f"   SVG bytes is None: {svg_bytes is None}")
    if svg_bytes:
        print(f"   SVG bytes length: {len(svg_bytes)}")
        print(f"   SVG preview (first 300 chars):\n{svg_bytes[:300]}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test base64 encoding
print("\n3. Testing base64 encoding...")
try:
    if svg_bytes:
        svg_b64 = base64.b64encode(svg_bytes).decode('utf-8')
        print(f"   Base64 length: {len(svg_b64)}")
        print(f"   Base64 preview (first 100 chars): {svg_b64[:100]}")
        
        # Test data URI
        data_uri = f"data:image/svg+xml;base64,{svg_b64}"
        print(f"   Data URI length: {len(data_uri)}")
        print(f"   Data URI preview (first 150 chars): {data_uri[:150]}")
    else:
        print("   SKIPPED: svg_bytes is None")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
