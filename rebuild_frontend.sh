#!/bin/bash

# Rebuild frontend to pick up Login.jsx changes

echo "🔄 Rebuilding frontend with updated Login page..."
echo ""

docker-compose build agency-web

echo ""
echo "🚀 Restarting frontend..."
docker-compose up -d agency-web

echo ""
echo "⏳ Waiting for frontend to start..."
sleep 5

echo ""
echo "✅ Done! Frontend rebuilt with:"
echo "   - Updated Login (uses /api/auth/login with email)"
echo "   - Auto-login after signup"
echo "   - Home links on both Login and Signup pages"
echo "   - Signup link on Login page"
echo ""
echo "Test it at:"
echo "   - Landing: http://localhost:3000/"
echo "   - Signup: http://localhost:3000/signup"
echo "   - Login: http://localhost:3000/login"
