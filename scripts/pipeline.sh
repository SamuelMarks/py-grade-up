#!/bin/sh
# pipeline.sh - A loose integration pipeline to confirm py-gradeup and mkconf work together.
#
# This script takes a target Python project, modernizes it with py-gradeup,
# scaffolds build infrastructure with mkconf, and verifies the resulting Docker image builds.

set -eu

TARGET_DIR="${1:-}"

if [ -z "$TARGET_DIR" ]; then
    echo "Usage: $0 <path_to_project>"
    echo "Example: $0 ../my-python-app"
    exit 1
fi

# Resolve absolute path for the target directory
TARGET_DIR=$(cd "$TARGET_DIR" && pwd)

echo "🚀 Starting Integration Pipeline for: $TARGET_DIR"
echo "------------------------------------------------------"

echo "Step 1: 🐍 Running py-gradeup to modernize Python syntax and dependencies..."
# Assuming py-gradeup is installed or we run it locally
if command -v py-gradeup > /dev/null 2>&1; then
    py-gradeup fix "$TARGET_DIR"
else
    # Fallback to running it from source if we are inside the py-gradeup repository
    python -m py_gradeup.cli fix "$TARGET_DIR"
fi

echo "------------------------------------------------------"
echo "Step 2: 🐳 Running mkconf to scaffold build files..."
# Use the local mkconf binary we found in the neighboring directory
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
MKCONF_BIN="$SCRIPT_DIR/../../mkconf/mkconf_bin"

if [ ! -x "$MKCONF_BIN" ]; then
    echo "❌ mkconf binary not found or not executable at $MKCONF_BIN"
    exit 1
fi

cd "$TARGET_DIR"
"$MKCONF_BIN" .

echo "------------------------------------------------------"
echo "Step 3: 🏗️  Verifying the build (Confirming it works!)..."

# mkconf generally creates multiple Dockerfiles (e.g. debian.Dockerfile, alpine.Dockerfile)
# Let's try to build the Debian one as our confirmation check.
if [ -f "debian.Dockerfile" ]; then
    echo "Building debian.Dockerfile to confirm everything runs..."
    docker build -f debian.Dockerfile -t "integration-test-image:latest" .
elif [ -f "Dockerfile" ]; then
    echo "Building standard Dockerfile..."
    docker build -t "integration-test-image:latest" .
else
    echo "⚠️ No Dockerfile found! Did mkconf generate correctly?"
    exit 1
fi

echo "------------------------------------------------------"
echo "✅ Pipeline Complete! The project was upgraded and containerized successfully."
