#!/bin/bash

# NetPulse One-Click Deployment Script

set -e

echo "🚀 NetPulse One-Click Deployment"
echo "================================="

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Warning: Running as root is not recommended"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Please install Docker first."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed."; exit 1; }

echo "✅ Prerequisites check passed"

# Setup environment
echo "📝 Setting up environment..."
bash ./scripts/check_env.sh generate

# Generate certificates
echo "🔐 Generating TLS certificates..."
bash ./scripts/generate_redis_certs.sh

# Start services
echo "🚀 Starting services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Verify deployment
echo "🔍 Verifying deployment..."
if docker compose ps | grep -q "Up"; then
    echo "✅ Services are running!"
    
    # Get API key
    source .env
    echo ""
    echo "🎉 Deployment successful!"
    echo "========================"
    echo "API Endpoint: http://localhost:9000"
    echo "API Key: $NETPULSE_SERVER__API_KEY"
    echo ""
    echo "Test your deployment:"
    echo "curl -H \"Authorization: Bearer $NETPULSE_SERVER__API_KEY\" http://localhost:9000/health"
    echo ""
    echo "View logs: docker compose logs -f"
    echo "Stop services: docker compose down"
else
    echo "❌ Deployment failed. Check logs:"
    docker compose logs
    exit 1
fi
