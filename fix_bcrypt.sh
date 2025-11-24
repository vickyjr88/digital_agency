#!/bin/bash

# Quick fix for bcrypt compatibility issue

echo "🔧 Fixing bcrypt version compatibility..."
echo ""

echo "Rebuilding API container with correct bcrypt version..."
docker-compose build agency-api

echo ""
echo "Restarting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for API to start..."
sleep 5

echo ""
echo "📊 Testing registration..."
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User"
  }' | jq .

echo ""
echo "✅ If you see a token above, registration is working!"
echo "   Otherwise, check logs: docker logs agency-api --tail 30"
