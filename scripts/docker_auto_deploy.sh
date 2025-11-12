#!/bin/bash

# NetPulse One-Click Deployment Script

set -e

echo "NetPulse One-Click Deployment"
echo "============================="

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    echo "Warning: Running as root is not recommended"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Please install Docker first."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed."; exit 1; }

echo "Prerequisites check passed"

# Setup environment - only generate if .env doesn't exist
echo "Setting up environment..."
if [ ! -f ".env" ]; then
    echo ".env file not found, generating new environment variables..."
    bash ./scripts/setup_env.sh generate
else
    echo ".env file exists, using existing configuration"
    bash ./scripts/setup_env.sh check
fi

# Generate certificates
echo "Generating TLS certificates..."
bash ./scripts/generate_redis_certs.sh

# Clear any existing system environment variables that might interfere
echo "Clearing system environment variables..."
unset NETPULSE_SERVER__API_KEY NETPULSE_REDIS__PASSWORD NETPULSE_LOG_LEVEL 2>/dev/null || true

# Load environment variables from .env file
echo "Loading environment variables from .env file..."
source .env

# Verify environment variables are loaded correctly
echo "Verifying environment variables..."
if [ "$NETPULSE_SERVER__API_KEY" = "change_this_api_key" ] || [ -z "$NETPULSE_SERVER__API_KEY" ]; then
    echo "NETPULSE_SERVER__API_KEY is not properly set"
    echo "Current value: $NETPULSE_SERVER__API_KEY"
    exit 1
fi

if [ "$NETPULSE_REDIS__PASSWORD" = "change_this_redis_password" ] || [ -z "$NETPULSE_REDIS__PASSWORD" ]; then
    echo "NETPULSE_REDIS__PASSWORD is not properly set"
    echo "Current value: $NETPULSE_REDIS__PASSWORD"
    exit 1
fi

echo "Environment variables loaded correctly:"
echo "  API Key: ${NETPULSE_SERVER__API_KEY:0:20}..."
echo "  Redis Password: ${NETPULSE_REDIS__PASSWORD:0:10}..."

# Stop existing services to ensure clean restart
echo "Stopping existing services..."
docker compose down 2>/dev/null || true

# Build Docker images
echo "Building Docker images..."
docker compose build

# Start services with explicit environment file
echo "Starting services..."
docker compose --env-file .env up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Verify environment variables in container
echo "Verifying environment variables in container..."
if docker compose exec controller env | grep -q "NETPULSE_SERVER__API_KEY=np_"; then
    echo "Environment variables are correctly set in container"
else
    echo "Environment variables are not correctly set in container"
    echo "Debugging container environment:"
    docker compose exec controller env | grep NETPULSE
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if .env file exists and has correct values"
    echo "2. Try: docker compose down && docker compose --env-file .env up -d"
    echo "3. Check Docker Compose logs: docker compose logs"
    exit 1
fi

# Verify deployment
echo "Verifying deployment..."
if docker compose ps | grep -q "Up"; then
    echo "Services are running!"
    
    echo ""
    echo "Deployment successful!"
    echo "===================="
    echo "API Endpoint: http://localhost:9000"
    echo "API Key: $NETPULSE_SERVER__API_KEY"
    echo ""
    echo "Test your deployment:"
    echo "curl -H \"X-API-KEY: $NETPULSE_SERVER__API_KEY\" http://localhost:9000/health"
    echo ""
    echo "View logs: docker compose logs -f"
    echo "Stop services: docker compose down"
else
    echo "Deployment failed. Check logs:"
    docker compose logs
    exit 1
fi
