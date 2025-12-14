#!/bin/bash

# NetPulse Environment Check Script

set -e

COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_NC='\033[0m' # No Color

print_status() {
    echo -e "${COLOR_BLUE}[INFO]${COLOR_NC} $1"
}

print_success() {
    echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_NC} $1"
}

print_warning() {
    echo -e "${COLOR_YELLOW}[WARNING]${COLOR_NC} $1"
}

print_error() {
    echo -e "${COLOR_RED}[ERROR]${COLOR_NC} $1"
}

check_env_file() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        print_status "Creating .env from template..."
        
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success ".env file created from template"
            print_warning "Please edit .env file and update the required values:"
            print_warning "  - NETPULSE_REDIS__PASSWORD"
            print_warning "  - NETPULSE_SERVER__API_KEY"
            return 1
        else
            print_error ".env.example template not found!"
            return 1
        fi
    fi
    
    print_success ".env file exists"
}

check_env_variables() {
    print_status "Checking required environment variables..."
    
    source .env
    
    local missing_vars=()
    
    if [ -z "$NETPULSE_REDIS__PASSWORD" ] || [ "$NETPULSE_REDIS__PASSWORD" = "change_this_redis_password" ]; then
        missing_vars+=("NETPULSE_REDIS__PASSWORD")
    fi
    
    if [ -z "$NETPULSE_SERVER__API_KEY" ] || [ "$NETPULSE_SERVER__API_KEY" = "change_this_api_key" ]; then
        missing_vars+=("NETPULSE_SERVER__API_KEY")
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Missing or default values found for required variables:"
        for var in "${missing_vars[@]}"; do
            print_error "  - $var"
        done
        print_status "Please update these variables in .env file"
        return 1
    fi
    
    print_success "All required environment variables are set"
}

generate_secure_values() {
    print_status "Generating secure values for environment variables..."
    
    local redis_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    local api_key="np_$(openssl rand -hex 32)"
    # Generate a random Vault token for dev mode (simple alphanumeric string)
    # Vault dev mode doesn't accept hvs. prefix, use plain random string
    local vault_token=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    
    # Create .env with secure values
    cat > .env << ENVEOF
# NetPulse Environment Configuration
# Generated on $(date)

# Redis Password (Required)
NETPULSE_REDIS__PASSWORD=$redis_password

# API Key (Required)
NETPULSE_SERVER__API_KEY=$api_key

# Optional: Time Zone
TZ=Asia/Shanghai

# Optional: Log Level (DEBUG, INFO, WARNING, ERROR)
NETPULSE_LOG__LEVEL=INFO

# Optional: Credential Provider (enabled by default, set enabled=false to disable)
NETPULSE_CREDENTIAL__ENABLED=true
NETPULSE_CREDENTIAL__NAME=vault_kv

# Optional: Vault KV v2 settings (token OR AppRole)
NETPULSE_CREDENTIAL__ADDR=http://vault:8200
NETPULSE_CREDENTIAL__ALLOWED_PATHS=kv/netpulse
NETPULSE_CREDENTIAL__VERIFY=false
NETPULSE_CREDENTIAL__CACHE_TTL=30

# Vault Token (randomly generated for each deployment)
# This token will be used as the root token for Vault dev mode
# For production, generate a proper token with limited permissions via Vault CLI
NETPULSE_VAULT_TOKEN=$vault_token
ENVEOF
    
    print_success "Secure environment variables generated!"
    print_warning "Your API Key: $api_key"
    print_warning "Vault Token: $vault_token"
    print_warning "Please save these credentials securely!"
}

check_certificates() {
    print_status "Checking TLS certificates..."
    
    if [ ! -f "redis/tls/redis.key" ] || [ ! -f "redis/tls/redis.crt" ]; then
        print_warning "TLS certificates not found, generating..."
        bash ./scripts/generate_redis_certs.sh
        print_success "TLS certificates generated"
    else
        print_success "TLS certificates exist"
    fi
}

main() {
    echo "NetPulse Environment Check"
    echo "========================="
    
    case "${1:-check}" in
        "check")
            if check_env_file && check_env_variables && check_certificates; then
                print_success "Environment check passed!"
                print_status "You can now run: docker compose up -d"
                return 0
            else
                print_error "Environment check failed!"
                print_status "Please fix the issues above before continuing"
                return 1
            fi
            ;;
        "generate")
            generate_secure_values
            check_certificates
            print_success "Environment setup complete!"
            print_status "You can now run: docker compose up -d"
            ;;
        *)
            echo "Usage: $0 {check|generate}"
            echo ""
            echo "Commands:"
            echo "  check    - Check if environment is properly configured"
            echo "  generate - Generate secure environment variables"
            ;;
    esac
}

main "$@"
