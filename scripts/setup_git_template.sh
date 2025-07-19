#!/bin/bash

# Setup Git commit template
echo "Setting up Git commit template..."

# Check if .gitmessage file exists
if [ ! -f ".gitmessage" ]; then
    echo "Error: .gitmessage file not found"
    exit 1
fi

# Set Git commit template
git config commit.template .gitmessage

echo "✓ Git commit template setup complete!"
echo "Template will be automatically loaded when running 'git commit'." 