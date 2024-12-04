#!/bin/bash

# Change to script directory
cd "$(dirname "$0")" || { echo "Failed to change directory"; exit 1; }

# Initialize and update all submodules recursively
git submodule update --init --recursive || { echo "Failed to update submodules"; exit 1; }

# Pull the latest changes for each submodule without specifying branch
git submodule foreach 'git pull' || { echo "Failed to pull submodules"; exit 1; }

echo "Copying files from submodules to project..."

cp -r .modules/safe-code-execution/open-webui/tools/* ./tools || { echo "Failed to copy files"; exit 1; }
cp -r .modules/safe-code-execution/open-webui/functions/* ./functions/actions || { echo "Failed to copy files"; exit 1; }

echo "Done!"