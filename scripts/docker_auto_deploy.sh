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

# Start Vault first
echo "Starting Vault..."
docker compose --env-file .env up -d vault

# Wait for Vault to be ready
echo "Waiting for Vault to start..."
sleep 10

# Initialize Vault if needed
if docker compose exec -T vault vault status 2>/dev/null | grep -q "Initialized.*false"; then
    echo "Initializing Vault..."
    init_output=$(docker compose exec -T vault vault operator init -key-shares=1 -key-threshold=1 -format=json 2>&1)
    
    # Extract keys using jq if available, otherwise use grep+sed
    if command -v jq >/dev/null 2>&1; then
        unseal_key=$(echo "$init_output" | jq -r '.unseal_keys_b64[0]' 2>/dev/null)
        root_token=$(echo "$init_output" | jq -r '.root_token' 2>/dev/null)
    else
        # Fallback: extract from JSON (handle multi-line format)
        unseal_key=$(echo "$init_output" | grep -A 2 '"unseal_keys_b64"' | grep -v '"unseal_keys_b64"' | grep -o '"[^"]*"' | head -1 | tr -d '"')
        root_token=$(echo "$init_output" | grep '"root_token"' | grep -o '"[^"]*"' | tail -1 | tr -d '"')
    fi
    
    if [ -z "$unseal_key" ] || [ -z "$root_token" ]; then
        echo "Error: Failed to extract unseal_key or root_token from Vault init"
        echo "$init_output"
        exit 1
    fi
    
    # Save to volume
    docker compose exec -T vault sh -c "echo '$unseal_key' > /vault/file/.unseal_key && chmod 600 /vault/file/.unseal_key"
    docker compose exec -T vault sh -c "echo '$root_token' > /vault/file/.root_token && chmod 600 /vault/file/.root_token"
    
    # Unseal Vault
    docker compose exec -T vault vault operator unseal "$unseal_key" > /dev/null
    
    # Enable KV v2 secret engine if not already enabled
    if ! docker compose exec -T -e VAULT_TOKEN="$root_token" vault vault secrets list 2>/dev/null | grep -q "secret/"; then
        docker compose exec -T -e VAULT_TOKEN="$root_token" vault vault secrets enable -path=secret kv-v2 > /dev/null 2>&1
        echo "KV v2 secret engine enabled at secret/"
    fi
    
    # Update .env file with unseal_key and root_token
    if [ -f ".env" ]; then
        # Update or add VAULT_UNSEAL_KEY with comment
        if grep -q "^VAULT_UNSEAL_KEY=" .env; then
            sed -i "s|^VAULT_UNSEAL_KEY=.*|VAULT_UNSEAL_KEY=$unseal_key|" .env
        else
            # Add with proper formatting before VAULT_TOKEN if exists
            if grep -q "^VAULT_TOKEN=" .env || grep -q "^# Vault Token" .env; then
                # Insert before VAULT_TOKEN section
                sed -i "/^# Vault Token/i\\
# Vault Unseal Key (Required for Vault unseal)\\
VAULT_UNSEAL_KEY=$unseal_key\\
" .env
            else
                # Append at end with proper formatting
                echo "" >> .env
                echo "# Vault Unseal Key (Required for Vault unseal)" >> .env
                echo "VAULT_UNSEAL_KEY=$unseal_key" >> .env
            fi
        fi
        # Update or add VAULT_TOKEN with comment
        if grep -q "^VAULT_TOKEN=" .env; then
            sed -i "s|^VAULT_TOKEN=.*|VAULT_TOKEN=$root_token|" .env
            # Ensure comment exists before VAULT_TOKEN
            if ! grep -q "^# Vault Token" .env; then
                sed -i "/^VAULT_TOKEN=/i\\
# Vault Token (Required for Vault integration, core component)\\
# This token is used for Vault authentication\\
" .env
            fi
        else
            echo "" >> .env
            echo "# Vault Token (Required for Vault integration, core component)" >> .env
            echo "# This token is used for Vault authentication" >> .env
            echo "VAULT_TOKEN=$root_token" >> .env
        fi
        echo "Vault unseal_key and root_token saved to .env"
    else
        echo "Warning: .env file not found, keys not saved to .env"
    fi
elif docker compose exec -T vault vault status 2>/dev/null | grep -q "Sealed.*true"; then
    echo "Vault is sealed, unsealing..."
    # Try .env first, then volume file
    unseal_key="${VAULT_UNSEAL_KEY:-}"
    root_token="${VAULT_TOKEN:-}"
    
    if [ -z "$unseal_key" ]; then
        unseal_key=$(docker compose exec -T vault cat /vault/file/.unseal_key 2>/dev/null || echo "")
    fi
    if [ -z "$root_token" ]; then
        root_token=$(docker compose exec -T vault cat /vault/file/.root_token 2>/dev/null || echo "")
    fi
    
    if [ -n "$unseal_key" ]; then
        docker compose exec -T vault vault operator unseal "$unseal_key" > /dev/null
        echo "Vault unsealed successfully"
        
        # Ensure KV v2 secret engine is enabled
        if [ -n "$root_token" ]; then
            if ! docker compose exec -T -e VAULT_TOKEN="$root_token" vault vault secrets list 2>/dev/null | grep -q "secret/"; then
                docker compose exec -T -e VAULT_TOKEN="$root_token" vault vault secrets enable -path=secret kv-v2 > /dev/null 2>&1
                echo "KV v2 secret engine enabled at secret/"
            fi
        fi
        
        # Update .env file if keys are found in volume but not in .env
        if [ -f ".env" ] && [ -n "$unseal_key" ] && [ -n "$root_token" ]; then
            if ! grep -q "^VAULT_UNSEAL_KEY=" .env; then
                # Add with proper formatting before VAULT_TOKEN if exists
                if grep -q "^VAULT_TOKEN=" .env || grep -q "^# Vault Token" .env; then
                    sed -i "/^# Vault Token/i\\
# Vault Unseal Key (Required for Vault unseal)\\
VAULT_UNSEAL_KEY=$unseal_key\\
" .env
                else
                    echo "" >> .env
                    echo "# Vault Unseal Key (Required for Vault unseal)" >> .env
                    echo "VAULT_UNSEAL_KEY=$unseal_key" >> .env
                fi
                echo "Added VAULT_UNSEAL_KEY to .env"
            else
                # Update if different
                current_key=$(grep "^VAULT_UNSEAL_KEY=" .env | cut -d'=' -f2-)
                if [ "$current_key" != "$unseal_key" ]; then
                    sed -i "s|^VAULT_UNSEAL_KEY=.*|VAULT_UNSEAL_KEY=$unseal_key|" .env
                    echo "Updated VAULT_UNSEAL_KEY in .env"
                fi
            fi
            if ! grep -q "^VAULT_TOKEN=" .env; then
                echo "" >> .env
                echo "# Vault Token (Required for Vault integration, core component)" >> .env
                echo "# This token is used for Vault authentication" >> .env
                echo "VAULT_TOKEN=$root_token" >> .env
                echo "Added VAULT_TOKEN to .env"
            else
                # Update if different
                current_token=$(grep "^VAULT_TOKEN=" .env | cut -d'=' -f2-)
                if [ "$current_token" != "$root_token" ]; then
                    sed -i "s|^VAULT_TOKEN=.*|VAULT_TOKEN=$root_token|" .env
                    echo "Updated VAULT_TOKEN in .env"
                fi
            fi
            
        fi
    else
        echo "Warning: Vault is sealed but unseal_key not found"
    fi
fi

# Start other services after Vault is ready
echo "Starting other services..."
docker compose --env-file .env up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 20

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
