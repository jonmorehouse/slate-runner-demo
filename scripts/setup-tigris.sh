#!/bin/bash

# Setup script for Tigris buckets
# This script helps you configure Tigris buckets for the Slate Runner demo

set -e

echo "========================================="
echo "Slate Runner Demo - Tigris Setup"
echo "========================================="
echo ""

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "Error: flyctl is not installed."
    echo "Please install it from: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

echo "This script will help you create Tigris buckets for the demo."
echo ""

# Get bucket names
read -p "Enter meta bucket name [slate-demo-meta]: " META_BUCKET
META_BUCKET=${META_BUCKET:-slate-demo-meta}

read -p "Enter runner bucket name [slate-demo-runner]: " RUNNER_BUCKET
RUNNER_BUCKET=${RUNNER_BUCKET:-slate-demo-runner}

echo ""
echo "Creating buckets..."
echo ""

# Create meta bucket
echo "Creating meta bucket: $META_BUCKET"
flyctl storage create --name "$META_BUCKET" --org personal || echo "Bucket may already exist"

# Create runner bucket
echo "Creating runner bucket: $RUNNER_BUCKET"
flyctl storage create --name "$RUNNER_BUCKET" --org personal || echo "Bucket may already exist"

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Get your Tigris credentials from: https://fly.io/dashboard"
echo "2. Update your .env file with:"
echo "   - AWS_ACCESS_KEY_ID"
echo "   - AWS_SECRET_ACCESS_KEY"
echo "   - SLATE_META_BUCKET=$META_BUCKET"
echo "   - SLATE_RUNNER_BUCKET=$RUNNER_BUCKET"
echo ""
echo "3. Start the control plane: cd control-plane && python app.py"
echo "4. Start a runner: cd runner && python main.py"
echo ""
