#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/frontend"

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dev dependencies..."
    npm install
fi

echo "Checking formatting (Prettier)..."
npm run format:check

echo "Linting JavaScript (ESLint)..."
npm run lint

echo "Frontend quality checks passed."
