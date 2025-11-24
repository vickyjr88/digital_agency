#!/bin/bash

# Emergency Fix: Clean Docker and Recreate Database

echo "🚨 Emergency Fix: Disk Full - Cleaning Docker..."
echo ""

# Stop all containers
echo "1️⃣ Stopping containers..."
docker-compose down

# Clean up Docker system
echo ""
echo "2️⃣ Cleaning Docker system (this may take a minute)..."
docker system prune -af --volumes

# Remove the corrupted postgres volume
echo ""
echo "3️⃣ Removing corrupted database volume..."
docker volume rm digital_agency_postgres_data 2>/dev/null || true

# Check disk space
echo ""
echo "4️⃣ Checking disk space..."
df -h | grep -E 'Filesystem|/System/Volumes/Data'

# Recreate everything
echo ""
echo "5️⃣ Recreating containers with fresh database..."
docker-compose up -d --build

# Wait for postgres to be healthy
echo ""
echo "6️⃣ Waiting for PostgreSQL to be ready..."
sleep 15

# Check status
echo ""
echo "7️⃣ Checking container status..."
docker-compose ps

# Check postgres logs
echo ""
echo "8️⃣ PostgreSQL logs:"
docker logs dexter-db --tail 10

# Check API logs
echo ""
echo "9️⃣ API logs:"
docker logs agency-api --tail 10

echo ""
echo "✅ Done! Try registering again:"
echo "   http://localhost:3000/signup"
echo ""
echo "Or test with curl:"
echo "curl -X POST http://localhost:8000/api/auth/register \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"email\":\"test@example.com\",\"password\":\"password123\",\"name\":\"Test User\"}'"
