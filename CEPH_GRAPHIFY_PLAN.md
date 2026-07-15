# Running Graphify on Ceph Components

## Objective
Systematically run Graphify with TOON and IBM Bob integration on each Ceph component in ~/ceph/src/, ending with the top-level ~/ceph/src directory.

## Components to Process (in order)
1. common
2. crimson
3. crush
4. crypto
5. global
6. include
7. java
8. librados
9. librbd
10. log
11. lss
12. mds
13. messages
14. mgr
15. mon
16. mount
17. msg
18. neorados
19. nvmeof
20. os
21. osd
22. osdc
23. perfglue
24. powerdns
25. pybind
26. rgw
27. rocksdb
28. seastar
29. telemetry
30. **src/ (top level)**

## Configuration
- TOON format is configured in `.graphify.toml` (33% more efficient than JSON)
- Bob skill is installed at `~/.bob/skills/graphify/SKILL.md`

## Commands to Run

For each component, run:
```bash
cd ~/ceph/src/<component>
python -m graphify . --no-cluster
```

For the top level:
```bash
cd ~/ceph/src
python -m graphify . --no-cluster
```

## Notes
- Using `--no-cluster` to skip LLM-based clustering (AST extraction only)
- This avoids the API key requirement for CMakeLists.txt files
- Each run will create a `graphify-out/` directory in the component folder
- TOON format will be used automatically per `.graphify.toml` configuration

## Automation Script
A bash script `run_graphify_on_ceph.sh` has been created to automate this process.

## Current Status
Ready to begin processing components systematically.