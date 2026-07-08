"""Tests for TOON encoder and decoder."""
import json
from graphify.toon import encode, decode


def test_round_trip_primitives():
    """Test encoding and decoding primitives."""
    test_cases = [
        None,
        True,
        False,
        42,
        3.14,
        "hello",
        "hello world",
        "with\nnewline",
        'with"quote',
    ]
    
    for value in test_cases:
        encoded = encode(value)
        decoded = decode(encoded)
        assert decoded == value, f"Failed for {value!r}: got {decoded!r}"


def test_round_trip_inline_arrays():
    """Test encoding and decoding inline arrays."""
    test_cases = [
        [],
        [1, 2, 3],
        ["a", "b", "c"],
        [True, False, None],
        [1, "two", 3.0, None, True],
    ]
    
    for value in test_cases:
        encoded = encode(value)
        decoded = decode(encoded)
        assert decoded == value, f"Failed for {value!r}: got {decoded!r}"


def test_round_trip_simple_object():
    """Test encoding and decoding simple objects."""
    obj = {
        "name": "Alice",
        "age": 30,
        "active": True,
        "score": 95.5,
        "notes": None,
    }
    
    encoded = encode(obj)
    decoded = decode(encoded)
    assert decoded == obj


def test_round_trip_nested_object():
    """Test encoding and decoding nested objects."""
    obj = {
        "user": {
            "name": "Bob",
            "email": "bob@example.com",
        },
        "settings": {
            "theme": "dark",
            "notifications": True,
        },
    }
    
    encoded = encode(obj)
    decoded = decode(encoded)
    assert decoded == obj


def test_round_trip_tabular_array():
    """Test encoding and decoding tabular arrays."""
    data = {
        "users": [
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob", "active": False},
            {"id": 3, "name": "Charlie", "active": True},
        ]
    }
    
    encoded = encode(data)
    decoded = decode(encoded)
    assert decoded == data


def test_round_trip_complex_graph():
    """Test encoding and decoding a graph-like structure."""
    graph = {
        "nodes": [
            {"id": "n1", "label": "Function A", "type": "function"},
            {"id": "n2", "label": "Function B", "type": "function"},
            {"id": "n3", "label": "Class C", "type": "class"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "relation": "calls"},
            {"source": "n2", "target": "n3", "relation": "uses"},
        ],
        "metadata": {
            "version": "1.0",
            "created": "2024-01-01",
            "node_count": 3,
            "edge_count": 2,
        },
    }
    
    encoded = encode(graph)
    decoded = decode(encoded)
    assert decoded == graph


def test_round_trip_with_special_chars():
    """Test encoding and decoding strings with special characters."""
    obj = {
        "path": "/home/user/file.txt",
        "url": "https://example.com/path?query=value",
        "code": 'def foo():\n    return "bar"',
        "escaped": 'Line 1\nLine 2\tTabbed',
    }
    
    encoded = encode(obj)
    decoded = decode(encoded)
    assert decoded == obj


def test_round_trip_empty_structures():
    """Test encoding and decoding empty structures."""
    test_cases = [
        {},
        {"empty_list": []},
        {"empty_obj": {}},
        {"nested": {"empty": {}}},
    ]
    
    for value in test_cases:
        encoded = encode(value)
        decoded = decode(encoded)
        assert decoded == value, f"Failed for {value!r}: got {decoded!r}"


def test_decode_manual_toon():
    """Test decoding manually written TOON."""
    toon_str = """name: Alice
age: 30
active: true
scores[3]: 95,87,92
tags[2]: python,testing"""
    
    decoded = decode(toon_str)
    expected = {
        "name": "Alice",
        "age": 30,
        "active": True,
        "scores": [95, 87, 92],
        "tags": ["python", "testing"],
    }
    assert decoded == expected


def test_decode_tabular_manual():
    """Test decoding manually written tabular TOON."""
    # Test root tabular array
    toon_str = """[3]{id,name,active}:
  1,Alice,true
  2,Bob,false
  3,Charlie,true"""
    
    decoded = decode(toon_str)
    expected = [
        {"id": 1, "name": "Alice", "active": True},
        {"id": 2, "name": "Bob", "active": False},
        {"id": 3, "name": "Charlie", "active": True},
    ]
    assert decoded == expected
    
    # Test object with tabular array
    toon_str2 = """users[3]{id,name,active}:
  1,Alice,true
  2,Bob,false
  3,Charlie,true"""
    
    decoded2 = decode(toon_str2)
    expected2 = {
        "users": [
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob", "active": False},
            {"id": 3, "name": "Charlie", "active": True},
        ]
    }
    assert decoded2 == expected2


def test_decode_nested_manual():
    """Test decoding manually written nested TOON."""
    toon_str = """user:
  name: Alice
  email: alice@example.com
settings:
  theme: dark
  notifications: true"""
    
    decoded = decode(toon_str)
    expected = {
        "user": {
            "name": "Alice",
            "email": "alice@example.com",
        },
        "settings": {
            "theme": "dark",
            "notifications": True,
        },
    }
    assert decoded == expected


def test_json_compatibility():
    """Test that TOON can encode/decode the same data as JSON."""
    test_data = {
        "string": "hello",
        "number": 42,
        "float": 3.14,
        "bool": True,
        "null": None,
        "array": [1, 2, 3],
        "object": {"nested": "value"},
        "mixed": [1, "two", {"three": 3}],
    }
    
    # Encode to both formats
    json_str = json.dumps(test_data)
    toon_str = encode(test_data)
    
    # Decode both
    from_json = json.loads(json_str)
    from_toon = decode(toon_str)
    
    # Should be equivalent
    assert from_json == from_toon == test_data


def test_size_reduction():
    """Test that TOON is more compact than JSON for typical data."""
    # Typical graph-like data
    data = {
        "nodes": [
            {"id": f"node{i}", "label": f"Node {i}", "type": "function"}
            for i in range(10)
        ],
        "edges": [
            {"source": f"node{i}", "target": f"node{i+1}", "relation": "calls"}
            for i in range(9)
        ],
    }
    
    json_str = json.dumps(data)
    toon_str = encode(data)
    
    # TOON should be smaller
    assert len(toon_str) < len(json_str)
    
    # But should decode to same data
    assert decode(toon_str) == data


def test_quoted_keys():
    """Test encoding and decoding keys that need quoting."""
    obj = {
        "normal_key": "value1",
        "key with spaces": "value2",
        "key:with:colons": "value3",
        "key,with,commas": "value4",
        "key\nwith\nnewlines": "value5",
    }
    
    encoded = encode(obj)
    decoded = decode(encoded)
    assert decoded == obj


def test_number_edge_cases():
    """Test encoding and decoding edge case numbers."""
    obj = {
        "zero": 0,
        "negative": -42,
        "large": 1234567890,
        "small_float": 0.0001,
        "negative_float": -3.14,
        "scientific": 1.23e10,
    }
    
    encoded = encode(obj)
    decoded = decode(encoded)
    
    # Check each value
    assert decoded["zero"] == 0
    assert decoded["negative"] == -42
    assert decoded["large"] == 1234567890
    assert abs(decoded["small_float"] - 0.0001) < 1e-10
    assert abs(decoded["negative_float"] - (-3.14)) < 1e-10
    assert abs(decoded["scientific"] - 1.23e10) < 1e5


if __name__ == "__main__":
    # Run all tests
    import sys
    
    test_functions = [
        test_round_trip_primitives,
        test_round_trip_inline_arrays,
        test_round_trip_simple_object,
        test_round_trip_nested_object,
        test_round_trip_tabular_array,
        test_round_trip_complex_graph,
        test_round_trip_with_special_chars,
        test_round_trip_empty_structures,
        test_decode_manual_toon,
        test_decode_tabular_manual,
        test_decode_nested_manual,
        test_json_compatibility,
        test_size_reduction,
        test_quoted_keys,
        test_number_edge_cases,
    ]
    
    failed = 0
    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\n{len(test_functions) - failed}/{len(test_functions)} tests passed")
    sys.exit(0 if failed == 0 else 1)

# Made with Bob
