#!/bin/bash -ex

SCRIPT_DIR="$(cd ${0%/*} && pwd -P)"
source "$SCRIPT_DIR/.env"

python3 "$SCRIPT_DIR/analyze_ev.py"

experiment_dir="$EXPERIMENTS_DIR/$1"

mkdir -p $experiment_dir
find "$PERFTEST_REPORTS_DIR" -exec cp \{\} "$experiment_dir" \; 2>/dev/null
