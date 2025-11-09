#!/bin/bash

# NetPulse Kubernetes Secrets Setup Script

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

generate_secure_values() {
    print_status "Generating secure values for Kubernetes secrets..."
    
    local redis_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    local api_key="np_$(openssl rand -hex 32)"
    
    # Create deployment secrets file (not in git)
    cat > k8s/00-secrets-deploy.yaml << SECRETSEOF
# 00-secrets/netpulse-secrets.yaml
# Generated on $(date) - DO NOT commit to version control
apiVersion: v1
kind: Secret
metadata:
  name: netpulse-secrets
  namespace: netpulse
type: Opaque
stringData:
  # Generated secure passwords - DO NOT commit to version control
  password: "$redis_password"
  api-key: "$api_key"
SECRETSEOF
    
    print_success "Secure secrets generated in k8s/00-secrets-deploy.yaml!"
    print_warning "Your API Key: $api_key"
    print_warning "Your Redis Password: $redis_password"
    print_warning "Please save these credentials securely!"
    print_status "Use: kubectl apply -f k8s/00-secrets-deploy.yaml"
}

apply_secrets() {
    print_status "Applying secrets to Kubernetes cluster..."
    
    # Check for deploy file first, then fall back to original
    local secrets_file=""
    if [ -f "k8s/00-secrets-deploy.yaml" ]; then
        secrets_file="k8s/00-secrets-deploy.yaml"
        print_status "Using generated secrets file: $secrets_file"
    elif [ -f "k8s/00-secrets.yaml" ]; then
        secrets_file="k8s/00-secrets.yaml"
        print_warning "Using original secrets file: $secrets_file"
        print_warning "Make sure you have updated the placeholder passwords!"
    else
        print_error "No secrets file found. Run 'generate' first or ensure k8s/00-secrets.yaml exists."
        return 1
    fi
    
    kubectl apply -f "$secrets_file"
    
    print_success "Secrets applied to Kubernetes cluster!"
    
    # Verify secrets were created
    if kubectl get secret netpulse-secrets >/dev/null 2>&1; then
        print_success "Secret 'netpulse-secrets' created successfully"
    else
        print_error "Failed to create secret 'netpulse-secrets'"
        return 1
    fi
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if kubectl is available
    if ! command -v kubectl >/dev/null 2>&1; then
        print_error "kubectl is required but not installed"
        return 1
    fi
    
    # Check if we can connect to cluster
    if ! kubectl cluster-info >/dev/null 2>&1; then
        print_error "Cannot connect to Kubernetes cluster"
        return 1
    fi
    
    print_success "Prerequisites check passed"
}

cleanup() {
    print_status "Cleaning up deployment files..."
    
    if [ -f "k8s/00-secrets-deploy.yaml" ]; then
        rm k8s/00-secrets-deploy.yaml
        print_success "Deployment secrets file removed"
    fi
}

main() {
    echo "NetPulse Kubernetes Secrets Setup"
    echo "=================================="
    
    case "${1:-help}" in
        "generate")
            check_prerequisites
            generate_secure_values
            print_success "Secrets generation complete!"
            print_status "Next step: kubectl apply -f k8s/00-secrets-deploy.yaml"
            ;;
        "apply")
            check_prerequisites
            apply_secrets
            print_success "Secrets applied to cluster!"
            print_status "Next step: kubectl apply -f k8s/01-redis.yaml"
            ;;
        "auto")
            check_prerequisites
            generate_secure_values
            apply_secrets
            print_success "Complete setup finished!"
            print_status "Next step: kubectl apply -f k8s/01-redis.yaml"
            print_warning "Deployment file k8s/00-secrets-deploy.yaml kept for reference"
            print_status "Run '$0 cleanup' to remove deployment files when done"
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|*)
            echo "Usage: $0 {generate|apply|auto|cleanup}"
            echo ""
            echo "Commands:"
            echo "  generate - Generate secure secrets file (k8s/00-secrets-deploy.yaml)"
            echo "  apply    - Apply secrets to Kubernetes cluster (auto-detect file)"
            echo "  auto     - Generate and apply secrets in one step (recommended)"
            echo "  cleanup  - Remove deployment files"
            echo ""
            echo "Deployment Options:"
            echo "  Option 1 (Auto): $0 auto"
            echo "  Option 2 (Manual): Edit k8s/00-secrets.yaml, then kubectl apply -f k8s/00-secrets.yaml"
            echo ""
            echo "File Management:"
            echo "  k8s/00-secrets-deploy.yaml - Deployment file (auto-generated, not in git)"
            echo "  $0 cleanup                 - Remove deployment files when done"
            echo ""
            echo "Examples:"
            echo "  $0 auto                    # Generate and apply secrets automatically"
            echo "  $0 generate && $0 apply    # Generate first, then apply"
            echo "  kubectl apply -f k8s/00-secrets.yaml  # Use manually edited file"
            echo "  $0 cleanup                 # Clean up temporary files"
            ;;
    esac
}

main "$@"
