#!/bin/bash

# Development startup script for Agent Hub

set -e

echo "🚀 Starting Agent Hub Development Environment"

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/state data/artifacts data/zvec logs

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 10

# Health check
echo "🔍 Checking service health..."
for i in {1..30}; do
    if curl -s http://localhost:7788/v1/health > /dev/null; then
        echo "✅ Agent Hub is ready!"
        echo "🌐 API: http://localhost:7788"
        echo "📚 Docs: http://localhost:7788/docs"
        exit 0
    fi
    echo "⏳ Waiting for services... ($i/30)"
    sleep 2
done

echo "❌ Service failed to start. Check logs:"
docker-compose logs
exit 1