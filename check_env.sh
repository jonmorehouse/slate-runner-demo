#!/bin/bash
# Check environment setup for SlateDB runner

echo "======================================"
echo "SlateDB Runner Environment Check"
echo "======================================"
echo ""

# Check for .env file
if [ -f .env ]; then
    echo "✓ .env file exists"
    
    # Check for required variables (without showing values)
    if grep -q "AWS_ACCESS_KEY_ID=" .env && [ -n "$(grep AWS_ACCESS_KEY_ID= .env | cut -d= -f2)" ]; then
        echo "✓ AWS_ACCESS_KEY_ID is set"
    else
        echo "✗ AWS_ACCESS_KEY_ID is missing or empty"
    fi
    
    if grep -q "AWS_SECRET_ACCESS_KEY=" .env && [ -n "$(grep AWS_SECRET_ACCESS_KEY= .env | cut -d= -f2)" ]; then
        echo "✓ AWS_SECRET_ACCESS_KEY is set"
    else
        echo "✗ AWS_SECRET_ACCESS_KEY is missing or empty"
    fi
    
    if grep -q "AWS_ENDPOINT_URL=" .env && [ -n "$(grep AWS_ENDPOINT_URL= .env | cut -d= -f2)" ]; then
        echo "✓ AWS_ENDPOINT_URL is set"
    else
        echo "✗ AWS_ENDPOINT_URL is missing or empty"
    fi
    
    if grep -q "SLATE_RUNNER_BUCKET=" .env && [ -n "$(grep SLATE_RUNNER_BUCKET= .env | cut -d= -f2)" ]; then
        echo "✓ SLATE_RUNNER_BUCKET is set"
    else
        echo "✗ SLATE_RUNNER_BUCKET is missing or empty"
    fi
    
else
    echo "✗ .env file not found"
    echo ""
    echo "To create .env file:"
    echo "  cp .env.example .env"
    echo "  # Then edit .env with your credentials"
fi

echo ""
echo "======================================"
echo "Quick Setup Guide"
echo "======================================"
echo "1. Copy .env.example to .env:"
echo "   cp .env.example .env"
echo ""
echo "2. Edit .env and set:"
echo "   - AWS_ACCESS_KEY_ID=your_access_key"
echo "   - AWS_SECRET_ACCESS_KEY=your_secret_key"
echo "   - AWS_ENDPOINT_URL=your_s3_endpoint"
echo "   - SLATE_RUNNER_BUCKET=your_bucket_name"
echo ""
echo "3. Source the environment:"
echo "   source .env  # or use dotenv"
echo ""
echo "4. Test SlateDB connection:"
echo "   python test_slatedb_minimal.py"
echo ""
