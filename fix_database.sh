#!/bin/bash

# Quick Fix Script for Database Connection

echo "🔧 Fixing Database Connection..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Show current DATABASE_URL
echo "Current DATABASE_URL in .env:"
grep "DATABASE_URL" .env || echo "  (not found)"
echo ""

# Update DATABASE_URL
echo "Updating DATABASE_URL to use 'postgres' service..."
if grep -q "DATABASE_URL" .env; then
    # Update existing line
    sed -i.bak 's|DATABASE_URL=.*|DATABASE_URL=postgresql://postgres:postgres@postgres:5432/dexter|' .env
    echo "✅ Updated DATABASE_URL"
else
    # Add new line
    echo "DATABASE_URL=postgresql://postgres:postgres@postgres:5432/dexter" >> .env
    echo "✅ Added DATABASE_URL"
fi

echo ""
echo "New DATABASE_URL:"
grep "DATABASE_URL" .env
echo ""

# Restart containers
echo "Restarting Docker containers..."
docker-compose down
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "🔍 Checking API logs:"
docker logs agency-api --tail 20

echo ""
echo "✅ Done! Try accessing:"
echo "   - API: http://localhost:8000/health"
echo "   - Signup: http://localhost:3000/signup"
