"""TOON (Token-Oriented Object Notation) encoder for Graphify.

Implements a subset of the TOON v3.3 specification for encoding graph data.
See: https://github.com/toon-format/spec
"""
from __future__ import annotations

import re
from typing import Any


def _needs_quoting(s: str, delimiter: str = ",") -> bool:
    """Check if a string needs quoting in TOON format.
    
    Per TOON spec §7.3: Unquoted keys match ^[A-Za-z_][A-Za-z0-9_.]*$
    Unquoted values additionally allow hyphens and must not look like numbers/booleans/null.
    """
    if not s:
        return True
    
    # Check for special literals that must be quoted to remain strings
    if s in ("true", "false", "null", "[]"):
        return True
    
    # Check if it looks like a number
    if re.match(r'^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$', s):
        return True
    
    # Check for delimiter, newlines, quotes, backslashes, or control chars
    if any(c in s for c in (delimiter, '\n', '\r', '"', '\\')):
        return True
    
    # Check for leading/trailing whitespace
    if s != s.strip():
        return True
    
    # Check for colon (structural character)
    if ':' in s:
        return True
    
    return False


def _escape_string(s: str) -> str:
    """Escape a string for TOON format per spec §7.1."""
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    s = s.replace('\t', '\\t')
    return s


def _format_value(value: Any, delimiter: str = ",", indent: int = 0) -> str:
    """Format a single value in TOON format."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        # Canonical number formatting per spec §2
        if isinstance(value, float):
            if value != value:  # NaN
                return "null"
            if value == float('inf') or value == float('-inf'):
                return "null"
            # Normalize -0 to 0
            if value == 0:
                value = 0
            # Format with sufficient precision
            s = f"{value:.17g}"  # Use 'g' format for clean output
            # Ensure no trailing zeros in fractional part
            if '.' in s and 'e' not in s.lower():
                s = s.rstrip('0').rstrip('.')
            return s
        return str(value)
    elif isinstance(value, str):
        if _needs_quoting(value, delimiter):
            return f'"{_escape_string(value)}"'
        return value
    elif isinstance(value, list):
        if not value:
            return "[]"
        # Check if all elements are primitives
        if all(isinstance(v, (str, int, float, bool, type(None))) for v in value):
            # Inline primitive array
            formatted = delimiter.join(_format_value(v, delimiter) for v in value)
            return f"[{len(value)}{delimiter if delimiter != ',' else ''}]: {formatted}"
        # Complex array - would need expansion (not implemented in this basic version)
        return "[]"
    elif isinstance(value, dict):
        # Will be handled by _encode_object
        return ""
    return str(value)


def _encode_object(obj: dict[str, Any], indent: int = 0, delimiter: str = ",") -> list[str]:
    """Encode an object as TOON lines."""
    lines = []
    indent_str = "  " * indent
    
    for key, value in obj.items():
        # Format key
        if _needs_quoting(key, delimiter):
            key_str = f'"{_escape_string(key)}"'
        else:
            key_str = key
        
        if isinstance(value, dict):
            if not value:
                # Empty object
                lines.append(f"{indent_str}{key_str}:")
            else:
                # Nested object
                lines.append(f"{indent_str}{key_str}:")
                lines.extend(_encode_object(value, indent + 1, delimiter))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{indent_str}{key_str}: []")
            elif all(isinstance(v, (str, int, float, bool, type(None))) for v in value):
                # Inline primitive array
                formatted_values = delimiter.join(_format_value(v, delimiter) for v in value)
                delim_marker = delimiter if delimiter != "," else ""
                lines.append(f"{indent_str}{key_str}[{len(value)}{delim_marker}]: {formatted_values}")
            elif all(isinstance(v, dict) for v in value):
                # Array of objects - check if tabular
                if value and _is_tabular(value):
                    # Tabular format
                    fields = list(value[0].keys())
                    field_str = delimiter.join(
                        f'"{_escape_string(f)}"' if _needs_quoting(f, delimiter) else f
                        for f in fields
                    )
                    delim_marker = delimiter if delimiter != "," else ""
                    lines.append(f"{indent_str}{key_str}[{len(value)}{delim_marker}]{{{field_str}}}:")
                    for item in value:
                        row_values = delimiter.join(
                            _format_value(item.get(f), delimiter) for f in fields
                        )
                        lines.append(f"{indent_str}  {row_values}")
                else:
                    # Expanded list items
                    delim_marker = delimiter if delimiter != "," else ""
                    lines.append(f"{indent_str}{key_str}[{len(value)}{delim_marker}]:")
                    for item in value:
                        if not item:
                            lines.append(f"{indent_str}  -")
                        else:
                            lines.append(f"{indent_str}  -")
                            lines.extend(_encode_object(item, indent + 2, delimiter))
            else:
                # Mixed array - use expanded form
                delim_marker = delimiter if delimiter != "," else ""
                lines.append(f"{indent_str}{key_str}[{len(value)}{delim_marker}]:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{indent_str}  -")
                        lines.extend(_encode_object(item, indent + 2, delimiter))
                    else:
                        formatted = _format_value(item, delimiter)
                        lines.append(f"{indent_str}  - {formatted}")
        else:
            # Primitive value
            formatted = _format_value(value, delimiter, indent)
            lines.append(f"{indent_str}{key_str}: {formatted}")
    
    return lines


def _is_tabular(items: list[dict]) -> bool:
    """Check if a list of objects is suitable for tabular format.
    
    Per spec: all items must have the same keys and all values must be primitives.
    """
    if not items:
        return False
    
    first_keys = set(items[0].keys())
    for item in items:
        if set(item.keys()) != first_keys:
            return False
        if not all(isinstance(v, (str, int, float, bool, type(None))) for v in item.values()):
            return False
    
    return True


def encode(data: Any, delimiter: str = ",") -> str:
    """Encode Python data to TOON format.
    
    Args:
        data: Python data structure (dict, list, or primitive)
        delimiter: Delimiter to use ("," for comma, "\t" for tab, "|" for pipe)
    
    Returns:
        TOON-formatted string
    """
    if data is None or isinstance(data, (bool, int, float, str)):
        # Root primitive
        return _format_value(data, delimiter)
    elif isinstance(data, list):
        if not data:
            return "[]"
        # Root array
        if all(isinstance(v, (str, int, float, bool, type(None))) for v in data):
            # Inline primitive array
            formatted = delimiter.join(_format_value(v, delimiter) for v in data)
            delim_marker = delimiter if delimiter != "," else ""
            return f"[{len(data)}{delim_marker}]: {formatted}"
        elif all(isinstance(v, dict) for v in data) and _is_tabular(data):
            # Tabular root array
            fields = list(data[0].keys())
            field_str = delimiter.join(
                f'"{_escape_string(f)}"' if _needs_quoting(f, delimiter) else f
                for f in fields
            )
            delim_marker = delimiter if delimiter != "," else ""
            lines = [f"[{len(data)}{delim_marker}]{{{field_str}}}:"]
            for item in data:
                row_values = delimiter.join(
                    _format_value(item.get(f), delimiter) for f in fields
                )
                lines.append(f"  {row_values}")
            return "\n".join(lines)
        else:
            # Expanded root array
            delim_marker = delimiter if delimiter != "," else ""
            lines = [f"[{len(data)}{delim_marker}]:"]
            for item in data:
                if isinstance(item, dict):
                    if not item:
                        lines.append("  -")
                    else:
                        lines.append("  -")
                        lines.extend(_encode_object(item, 2, delimiter))
                else:
                    formatted = _format_value(item, delimiter)
                    lines.append(f"  - {formatted}")
            return "\n".join(lines)
    elif isinstance(data, dict):
        if not data:
            return ""
        # Root object
        lines = _encode_object(data, 0, delimiter)
        return "\n".join(lines)
    else:
        raise TypeError(f"Cannot encode type {type(data).__name__} to TOON")

def _unescape_string(s: str) -> str:
    """Unescape a TOON string per spec §7.1."""
    s = s.replace('\\n', '\n')
    s = s.replace('\\r', '\r')
    s = s.replace('\\t', '\t')
    s = s.replace('\\"', '"')
    s = s.replace('\\\\', '\\')
    return s


def _parse_value(s: str, delimiter: str = ",") -> Any:
    """Parse a single TOON value."""
    s = s.strip()
    
    if not s:
        return None
    
    # Check for literals
    if s == "null":
        return None
    elif s == "true":
        return True
    elif s == "false":
        return False
    elif s == "[]":
        return []
    
    # Check for quoted string
    if s.startswith('"') and s.endswith('"'):
        return _unescape_string(s[1:-1])
    
    # Try to parse as number
    try:
        if '.' in s or 'e' in s.lower():
            return float(s)
        else:
            return int(s)
    except ValueError:
        pass
    
    # Unquoted string
    return s


def _parse_inline_array(content: str, delimiter: str = ",") -> list:
    """Parse an inline array like [3]: a,b,c"""
    values = []
    current = []
    in_quotes = False
    escape_next = False
    
    for char in content:
        if escape_next:
            current.append(char)
            escape_next = False
        elif char == '\\':
            current.append(char)
            escape_next = True
        elif char == '"':
            current.append(char)
            in_quotes = not in_quotes
        elif char == delimiter and not in_quotes:
            values.append(_parse_value(''.join(current), delimiter))
            current = []
        else:
            current.append(char)
    
    if current:
        values.append(_parse_value(''.join(current), delimiter))
    
    return values


def _parse_tabular_row(line: str, fields: list[str], delimiter: str = ",") -> dict:
    """Parse a tabular row into a dict."""
    values = []
    current = []
    in_quotes = False
    escape_next = False
    
    for char in line:
        if escape_next:
            current.append(char)
            escape_next = False
        elif char == '\\':
            current.append(char)
            escape_next = True
        elif char == '"':
            current.append(char)
            in_quotes = not in_quotes
        elif char == delimiter and not in_quotes:
            values.append(_parse_value(''.join(current), delimiter))
            current = []
        else:
            current.append(char)
    
    if current:
        values.append(_parse_value(''.join(current), delimiter))
    
    # Pad with None if not enough values
    while len(values) < len(fields):
        values.append(None)
    
    return dict(zip(fields, values))


def decode(toon_str: str, delimiter: str = ",") -> Any:
    """Decode TOON format to Python data.
    
    Args:
        toon_str: TOON-formatted string
        delimiter: Delimiter used ("," for comma, "\t" for tab, "|" for pipe)
    
    Returns:
        Python data structure (dict, list, or primitive)
    """
    lines = toon_str.split('\n')
    if not lines:
        return None
    
    # Check for root primitive or inline array
    first_line = lines[0].strip()
    if not first_line:
        # Empty string means empty object
        return {}
    
    # Root inline array: [N]: values or [N|]: values
    if first_line.startswith('[') and ']:' in first_line:
        bracket_end = first_line.index(']')
        colon_pos = first_line.index(':', bracket_end)
        content = first_line[colon_pos + 1:].strip()
        return _parse_inline_array(content, delimiter)
    
    # Root tabular array: [N]{fields}: or [N|]{fields}:
    if first_line.startswith('[') and ']{' in first_line and '}:' in first_line:
        # Extract fields
        brace_start = first_line.index(']{') + 2
        brace_end = first_line.index('}:', brace_start)
        fields_str = first_line[brace_start:brace_end]
        fields = _parse_inline_array(fields_str, delimiter)
        
        # Parse rows
        result = []
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            # Remove leading indentation
            if line.startswith('  '):
                row_data = line[2:]
            else:
                row_data = line
            result.append(_parse_tabular_row(row_data, fields, delimiter))
        return result
    
    # Root expanded array: [N]: or [N|]:
    if first_line.startswith('[') and first_line.endswith(':'):
        result = []
        i = 1
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if not stripped:
                i += 1
                continue
            
            # Check for list item marker
            if stripped.startswith('- '):
                # Inline item
                value_str = stripped[2:].strip()
                result.append(_parse_value(value_str, delimiter))
                i += 1
            elif stripped == '-':
                # Object item follows
                obj = {}
                i += 1
                # Collect object lines
                base_indent = len(line) - len(line.lstrip())
                while i < len(lines):
                    next_line = lines[i]
                    if not next_line.strip():
                        i += 1
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= base_indent:
                        break
                    # Parse object line
                    obj_line = next_line[base_indent + 2:]  # Remove base + 2 spaces
                    if ':' in obj_line:
                        key, value = _parse_object_line(obj_line, delimiter, lines, i, base_indent + 2)
                        if key:
                            obj[key] = value
                    i += 1
                result.append(obj)
            else:
                i += 1
        return result
    
    # Root object or primitive
    if ':' not in first_line:
        # Root primitive
        return _parse_value(first_line, delimiter)
    
    # Root object
    result = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        
        indent = len(line) - len(line.lstrip())
        if indent > 0:
            i += 1
            continue
        
        key, value = _parse_object_line(line, delimiter, lines, i, 0)
        if key:
            result[key] = value
        i += 1
    
    return result


def _parse_object_line(line: str, delimiter: str, all_lines: list[str], line_idx: int, base_indent: int) -> tuple[str | None, Any]:
    """Parse a single object line and return (key, value).
    
    Returns (None, None) if the line should be skipped.
    """
    stripped = line.strip()
    if not stripped or ':' not in stripped:
        return None, None
    
    # Find the colon that separates key from value
    # Need to handle quoted keys properly
    key = None
    remainder = ""
    value_part = ""
    
    if stripped.startswith('"'):
        # Quoted key
        escape_next = False
        i = 1
        key_chars = []
        while i < len(stripped):
            char = stripped[i]
            if escape_next:
                key_chars.append(char)
                escape_next = False
            elif char == '\\':
                key_chars.append(char)
                escape_next = True
            elif char == '"':
                # End of quoted key
                key = _unescape_string(''.join(key_chars))
                # Find colon after quote
                rest = stripped[i + 1:]
                if ':' in rest:
                    colon_pos = rest.index(':')
                    remainder = rest[:colon_pos].strip()
                    value_part = rest[colon_pos + 1:].strip()
                break
            else:
                key_chars.append(char)
            i += 1
    else:
        # Unquoted key
        colon_pos = stripped.index(':')
        key_part = stripped[:colon_pos].strip()
        value_part = stripped[colon_pos + 1:].strip()
        
        # Find array notation if present
        if '[' in key_part:
            bracket_pos = key_part.index('[')
            key = key_part[:bracket_pos].strip()
            remainder = key_part[bracket_pos:]
        else:
            key = key_part
            remainder = ""
    
    # Check for array notation: key[N]: or key[N]{fields}:
    if remainder.startswith('['):
        bracket_end = remainder.index(']')
        array_size_str = remainder[1:bracket_end]
        # Remove delimiter marker if present
        if array_size_str and array_size_str[-1] in (',', '\t', '|'):
            array_size_str = array_size_str[:-1]
        
        # Check for tabular format: {fields}
        if ']{' in remainder and '}' in remainder:
            # Tabular array
            brace_start = remainder.index(']{') + 2
            brace_end = remainder.index('}', brace_start)
            fields_str = remainder[brace_start:brace_end]
            fields = _parse_inline_array(fields_str, delimiter)
            
            # Parse rows from following lines
            result = []
            i = line_idx + 1
            while i < len(all_lines):
                next_line = all_lines[i]
                if not next_line.strip():
                    i += 1
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= base_indent:
                    break
                row_data = next_line[base_indent + 2:]  # Remove indentation
                result.append(_parse_tabular_row(row_data, fields, delimiter))
                i += 1
            return key, result
        
        # Check for inline array: key[N]: values
        if value_part:
            return key, _parse_inline_array(value_part, delimiter)
        
        # Expanded array
        result = []
        i = line_idx + 1
        while i < len(all_lines):
            next_line = all_lines[i]
            if not next_line.strip():
                i += 1
                continue
            next_indent = len(next_line) - len(next_line.lstrip())
            if next_indent <= base_indent:
                break
            
            next_stripped = next_line.strip()
            if next_stripped.startswith('- '):
                # Inline item
                value_str = next_stripped[2:].strip()
                result.append(_parse_value(value_str, delimiter))
            elif next_stripped == '-':
                # Object item follows
                obj = {}
                i += 1
                while i < len(all_lines):
                    obj_line = all_lines[i]
                    if not obj_line.strip():
                        i += 1
                        continue
                    obj_indent = len(obj_line) - len(obj_line.lstrip())
                    if obj_indent <= next_indent:
                        break
                    obj_key, obj_value = _parse_object_line(obj_line, delimiter, all_lines, i, next_indent + 2)
                    if obj_key:
                        obj[obj_key] = obj_value
                    i += 1
                result.append(obj)
                continue
            i += 1
        return key, result
    
    # Simple value or nested object
    if not value_part:
        # Nested object follows
        obj = {}
        i = line_idx + 1
        while i < len(all_lines):
            next_line = all_lines[i]
            if not next_line.strip():
                i += 1
                continue
            next_indent = len(next_line) - len(next_line.lstrip())
            if next_indent <= base_indent:
                break
            obj_key, obj_value = _parse_object_line(next_line, delimiter, all_lines, i, base_indent + 2)
            if obj_key:
                obj[obj_key] = obj_value
            i += 1
        return key, obj
    
    # Simple value
    return key, _parse_value(value_part, delimiter)


# Made with Bob
