#!/bin/bash
# Quick test script for Slate Runner Demo

set -e

echo "🧪 Slate Runner Demo - Quick Test"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }
echo "✅ Python OK"
echo ""

# Check required Python packages
echo "Checking Python dependencies..."
python3 -c "import flask" 2>/dev/null || { echo "❌ Flask not installed. Run: pip install -r control-plane/requirements.txt"; exit 1; }
python3 -c "import boto3" 2>/dev/null || { echo "❌ boto3 not installed. Run: pip install -r runner/requirements.txt"; exit 1; }
echo "✅ Python packages OK"
echo ""

# Check environment variables
echo "Checking environment variables..."
required_vars="AWS_ENDPOINT_URL AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY"
for var in $required_vars; do
    if [ -z "${!var}" ]; then
        echo "❌ $var not set"
        echo "Please set required environment variables:"
        echo "  export AWS_ENDPOINT_URL=<your-tigris-url>"
        echo "  export AWS_ACCESS_KEY_ID=<your-key>"
        echo "  export AWS_SECRET_ACCESS_KEY=<your-secret>"
        exit 1
    fi
done
echo "✅ Environment variables OK"
echo ""

# Test S3 connectivity
echo "Testing S3 connectivity..."
python3 << 'EOF'
import boto3
import os

s3 = boto3.client(
    's3',
    endpoint_url=os.getenv('AWS_ENDPOINT_URL'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'auto')
)

try:
    s3.list_buckets()
    print("✅ S3 connection successful")
except Exception as e:
    print(f"❌ S3 connection failed: {e}")
    exit(1)
EOF

echo ""
echo "=================================="
echo "✅ All prerequisites met!"
echo ""
echo "Ready to run demo:"
echo "  1. Terminal 1: cd control-plane && python app.py"
echo "  2. Terminal 2: cd runner && python main.py"
echo "  3. Browser: http://localhost:5000"
echo "=================================="
