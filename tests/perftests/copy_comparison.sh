#!/bin/bash

SCRIPT_DIR="$(cd ${0%/*} && pwd -P)"
source "$SCRIPT_DIR/.env"

echo dir: "$1"

cp "$SCRIPT_DIR/comparison.csv" "$1/comparison.csv"
cp "$SCRIPT_DIR/comparison.json" "$1/comparison.json"
cp "$SCRIPT_DIR/events.png" "$1/events.png"
