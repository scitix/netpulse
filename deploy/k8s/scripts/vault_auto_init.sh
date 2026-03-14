#!/bin/sh
# NetPulse Vault Auto-Initialization and Guardian Script
# This script handles initial setup AND keeps Vault unsealed AND aligns tokens.

# Use set -e for the initial setup, but we'll be more careful in the loop
set -e
export VAULT_ADDR='http://vault:8200'

# Tool: Clean strings from potential hidden characters or newlines
clean_str() {
    echo "$1" | tr -d '\r' | tr -d '\n' | tr -d ' '
}

echo "Starting Vault initialization process..."

# 1. Wait for Vault to be ready
until vault status > /dev/null 2>&1 || [ $? -ne 127 ]; do
    echo "Waiting for Vault service at $VAULT_ADDR..."
    sleep 2
done

# 2. Initialization
if ! vault status | grep -q "Initialized.*true"; then
    echo "Vault is not initialized. Initializing now..."
    INIT_RESPONSE=$(vault operator init -key-shares=1 -key-threshold=1)
    
    UNSEAL_KEY=$(clean_str "$(echo "$INIT_RESPONSE" | grep "Unseal Key 1:" | awk '{print $NF}')")
    ROOT_TOKEN=$(clean_str "$(echo "$INIT_RESPONSE" | grep "Initial Root Token:" | awk '{print $NF}')")
    
    echo "$UNSEAL_KEY" > /vault/data/unseal.key
    echo "$ROOT_TOKEN" > /vault/data/root.token
    echo "Vault initialized. Keys saved to /vault/data/"
fi

# 3. Guardian & Alignment Loop
echo "Entering Guardian and Alignment loop..."
# Disable set -e so the loop doesn't kill the container on transient Vault errors
set +e 

while true; do
    # Check if Vault is reachable
    if ! vault status > /dev/null 2>&1 && [ $? -eq 127 ]; then
        echo "Vault binary not found or unreachable. Retrying..."
        sleep 5
        continue
    fi

    # Management: Unseal
    if vault status 2>&1 | grep -q "Sealed.*true"; then
        echo "Vault is sealed. Attempting automatic unseal..."
        if [ -f /vault/data/unseal.key ]; then
            K=$(clean_str "$(cat /vault/data/unseal.key)")
            if vault operator unseal "$K" > /dev/null 2>&1; then
                echo "Vault unsealed successfully."
            else
                echo "Warning: Unseal failed."
            fi
        fi
    fi

    # Management: Token Alignment & KV Engine
    if vault status 2>&1 | grep -q "Sealed.*false"; then
        # Ensure we have the root token to work with
        if [ -f /vault/data/root.token ]; then
            RT=$(clean_str "$(cat /vault/data/root.token)")
            
            # Align .env token
            if [ -n "$NETPULSE_VAULT_TOKEN" ]; then
                # Check if current token in .env is already valid
                if ! VAULT_TOKEN="$NETPULSE_VAULT_TOKEN" vault token lookup > /dev/null 2>&1; then
                    echo "Target token in .env is invalid or not yet aligned. Aligning..."
                    # Note: ID cannot start with 'hvs.' prefix
                    if VAULT_TOKEN="$RT" vault token create -id="$NETPULSE_VAULT_TOKEN" -policy="root" > /dev/null 2>&1; then
                        echo "Token alignment successful: $NETPULSE_VAULT_TOKEN"
                    else
                        echo "Error: Token alignment failed. Check if NETPULSE_VAULT_TOKEN starts with 'hvs.' (not allowed for custom IDs)."
                    fi
                fi
            fi

            # Ensure KV engine
            if ! VAULT_TOKEN="$RT" vault secrets list | grep -q "^kv/"; then
                echo "Enabling KV v2 secrets engine..."
                VAULT_TOKEN="$RT" vault secrets enable -path=kv kv-v2 > /dev/null 2>&1
            fi
        fi
    fi
    
    sleep 10
done
