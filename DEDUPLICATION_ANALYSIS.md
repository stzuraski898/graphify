# Graphify Deduplication Analysis for Ceph

## Executive Summary

The Ceph graphify output contains significant duplication of common type nodes (e.g., `DaemonServer` appears 6 times, `string` appears 41 times, `map` appears 10+ times). This is **by design** to preserve file-level context, but can be optimized for large C++ codebases.

## Duplicate Examples from Ceph Graph

### DaemonServer (6 instances)
```json
{
  "id": "activepymodules_cc_daemonserver",
  "label": "DaemonServer",
  "source_file": "",
  "community": 28,
  "community_name": "ActivePyModules::ActivePyModules"
},
{
  "id": "daemonserver_cc_daemonserver",
  "label": "DaemonServer",
  "source_file": "",
  "community": 15,
  "community_name": "DaemonServer"
},
{
  "id": "mgr_h_daemonserver",
  "label": "DaemonServer",
  "source_file": "",
  "community": 13,
  "community_name": "Mgr"
},
{
  "id": "pymoduleregistry_cc_daemonserver",
  "label": "DaemonServer",
  "source_file": "",
  "community": 86,
  "community_name": "active_start"
},
{
  "id": "activepymodules_daemonserver",
  "label": "DaemonServer",
  "source_file": "ActivePyModules.h",
  "community": 63,
  "community_name": "ActivePyModules.h"
},
{
  "id": "daemonserver_daemonserver",
  "label": "DaemonServer",
  "source_file": "DaemonServer.h",
  "community": 4,
  "community_name": "DaemonServer"
}
```

### Common Types with High Duplication
- **string**: 41 instances
- **map**: 10 instances
- **vector**: Multiple instances
- **bufferlist**: Multiple instances (Ceph-specific)
- **PyObject**: Multiple instances

## Why Duplicates Exist

### Design Rationale

Graphify uses **file-scoped node IDs** following this pattern:
```
{file_stem}_{symbol_name}
```

This design choice provides:

1. **Context Preservation**: Each file's usage represents a different relationship
2. **Community Detection**: Enables clustering files by shared dependencies
3. **Cross-file Analysis**: Tracks which files depend on which symbols
4. **Source Location**: Maintains precise location information

### Example: Why 6 DaemonServer Nodes?

Each node represents a **different usage context**:
- `daemonserver_daemonserver` - The **definition** in DaemonServer.h
- `activepymodules_cc_daemonserver` - **Used by** ActivePyModules.cc
- `mgr_h_daemonserver` - **Referenced in** Mgr.h
- etc.

This allows queries like:
- "Which files depend on DaemonServer?"
- "What's the dependency chain from Mgr to DaemonServer?"
- "Which community does each usage belong to?"

## The Problem

For large C++ codebases like Ceph:

### Statistics from Ceph Graph
- **Total nodes**: 2,021
- **Estimated duplicates**: ~500-700 nodes (25-35%)
- **Common types**: `string`, `map`, `vector`, `bufferlist`, `PyObject`, etc.

### Issues
1. **Graph Inflation**: 25-35% of nodes are duplicates of common types
2. **Visualization Clutter**: Common types appear everywhere, obscuring real architecture
3. **God Nodes**: Types like `map` become "god nodes" with 41 edges
4. **Report Noise**: Community hubs list includes `string`, `map` alongside actual classes

## Solution: Selective Deduplication

### Strategy

**Deduplicate standard library and framework types, preserve user-defined classes.**

### What to Deduplicate

#### C++ Standard Library Types
```python
CPP_STDLIB_TYPES = {
    # Containers
    "vector", "list", "deque", "map", "set", "unordered_map",
    
    # Strings
    "string", "string_view",
    
    # Smart pointers
    "unique_ptr", "shared_ptr", "weak_ptr",
    
    # Utilities
    "pair", "tuple", "optional", "function",
    
    # Threading
    "mutex", "atomic", "thread",
    
    # Streams
    "ostream", "istream", "stringstream",
}
```

#### Ceph Framework Types
```python
FRAMEWORK_TYPES = {
    "bufferlist", "Context", "Formatter", "epoch_t", "utime_t",
    "entity_addr_t", "Connection", "Message", "ref_t",
    "PyObject", "PyThreadState", "PyTypeObject",
}
```

### What NOT to Deduplicate

**User-defined classes** like:
- `DaemonServer` - Application class
- `ActivePyModules` - Application class
- `MgrClient` - Application class
- `ClusterState` - Application class

These should remain file-scoped because:
1. They represent actual architecture
2. Their usage patterns are meaningful
3. Community detection needs them

## Implementation

### New Module: `graphify/dedup_types.py`

```python
def deduplicate_common_types(G: nx.Graph, verbose: bool = False) -> nx.Graph:
    """Merge file-scoped nodes for common types into canonical nodes."""
    # Identifies common types (string, map, vector, etc.)
    # Merges all instances into single canonical node
    # Preserves all edges (deduplicated)
    # Returns cleaned graph
```

### Integration Points

#### Option A: Post-Processing (Recommended)
Add to `graphify/build.py` after graph construction:

```python
from .dedup_types import deduplicate_common_types

def build(...):
    # ... existing code ...
    
    # Optional deduplication
    if config.get("deduplication", {}).get("enabled", False):
        G = deduplicate_common_types(G, verbose=True)
    
    return G
```

#### Option B: CLI Flag
Add to `graphify/__main__.py`:

```bash
graphify build --deduplicate-types
```

### Configuration

Add to `.graphify.toml`:

```toml
[deduplication]
enabled = true

# Additional project-specific types to deduplicate
additional_types = [
    "CephContext",
    "MonClient",
    "Objecter",
]

# Types to never deduplicate (even if they match patterns)
exclude_types = [
    "MyCustomString",  # Custom string wrapper
]
```

## Expected Impact on Ceph Graph

### Before Deduplication
- **Nodes**: 2,021
- **Edges**: 3,543
- **Communities**: 192

### After Deduplication (Estimated)
- **Nodes**: ~1,400-1,500 (30% reduction)
- **Edges**: ~3,200-3,400 (slight reduction due to edge deduplication)
- **Communities**: ~180-190 (cleaner communities)

### Specific Improvements

1. **God Nodes Eliminated**:
   - `string` (41 instances) → 1 canonical node
   - `map` (10 instances) → 1 canonical node
   - `vector` → 1 canonical node

2. **Cleaner Community Hubs**:
   - Remove: `string`, `map`, `vector` from hub list
   - Keep: `DaemonServer`, `ActivePyModules`, `MgrClient`

3. **Better Visualization**:
   - Less clutter from common types
   - Focus on actual architecture
   - Clearer dependency chains

## Trade-offs

### Advantages
✅ Reduces graph size by 25-35%
✅ Cleaner visualization
✅ More meaningful "god nodes" list
✅ Faster graph operations
✅ Better community detection for application code

### Disadvantages
❌ Loses file-specific context for common types
❌ Can't answer "which files use std::string?"
❌ Slightly more complex implementation

### Mitigation
- Keep deduplication **optional** (config flag)
- Only deduplicate **well-known types**
- Preserve **all edges** (just merge endpoints)
- Add `_deduplicated_from` attribute to track original count

## Recommendations

### For Ceph Specifically

1. **Enable deduplication** for standard library types
2. **Add Ceph-specific types** to deduplication list:
   ```python
   CEPH_TYPES = {
       "bufferlist", "Context", "Formatter",
       "epoch_t", "utime_t", "entity_addr_t",
       "Connection", "Message", "ref_t",
   }
   ```

3. **Keep file-scoped** for application classes:
   - `DaemonServer`, `ActivePyModules`, `MgrClient`, etc.

### General Guidelines

**Deduplicate if**:
- Type is from standard library
- Type appears in >10 files
- Type is a utility/framework class
- Context doesn't matter for analysis

**Keep file-scoped if**:
- Type is application-specific
- Usage patterns are meaningful
- Type represents architecture
- Community detection needs it

## Alternative Approaches

### 1. Namespace-Based Deduplication
Only deduplicate types from `std::`, `boost::`, etc.

**Pros**: More precise
**Cons**: Requires namespace tracking

### 2. Frequency-Based Deduplication
Deduplicate any type appearing in >N files

**Pros**: Automatic
**Cons**: May deduplicate important types

### 3. Hybrid Approach (Recommended)
Combine whitelist (stdlib) + frequency threshold (>20 files)

**Pros**: Best of both worlds
**Cons**: More complex logic

## Conclusion

The duplication in Graphify's Ceph output is **intentional and valuable** for preserving context, but can be **selectively optimized** for large C++ codebases. The proposed solution:

1. **Preserves** the file-scoped design for application code
2. **Deduplicates** only common types that add noise
3. **Maintains** all relationship information
4. **Improves** visualization and analysis

This approach reduces graph size by ~30% while maintaining the semantic richness that makes Graphify valuable for understanding large codebases.