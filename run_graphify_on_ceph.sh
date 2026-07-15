#!/bin/bash

# Script to run graphify on each Ceph component
# Uses TOON format as configured in .graphify.toml

set -e

CEPH_SRC="$HOME/ceph/src"
COMPONENTS=(
    "common"
    "crimson"
    "crush"
    "crypto"
    "global"
    "include"
    "java"
    "librados"
    "librbd"
    "log"
    "lss"
    "mds"
    "messages"
    "mgr"
    "mon"
    "mount"
    "msg"
    "neorados"
    "nvmeof"
    "os"
    "osd"
    "osdc"
    "perfglue"
    "powerdns"
    "pybind"
    "rgw"
    "rocksdb"
    "seastar"
    "telemetry"
)

echo "Starting graphify runs on Ceph components..."
echo "Using TOON format (configured in .graphify.toml)"
echo ""

for component in "${COMPONENTS[@]}"; do
    echo "========================================="
    echo "Processing: $component"
    echo "========================================="
    
    cd "$CEPH_SRC/$component"
    
    # Run graphify with no-cluster to skip LLM-based clustering
    # This will do AST extraction only
    python -m graphify . --no-cluster || {
        echo "Warning: graphify failed for $component, continuing..."
    }
    
    echo ""
done

echo "========================================="
echo "Processing: top-level src/"
echo "========================================="
cd "$CEPH_SRC"
python -m graphify . --no-cluster || {
    echo "Warning: graphify failed for top-level src/, continuing..."
}

echo ""
echo "All graphify runs complete!"

# Made with Bob
