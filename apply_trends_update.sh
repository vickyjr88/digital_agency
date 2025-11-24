#!/bin/bash

# Update Database Schema for Trends

echo "🔄 Updating Database Schema for Trends..."
echo ""

# We need to recreate the database to add the new 'trends' table and relationships
echo "⚠️  WARNING: This will RESET the database."
echo "    All existing users and data will be lost."
echo ""
echo "1️⃣ Stopping containers..."
docker-compose down

echo ""
echo "2️⃣ Removing database volume..."
docker volume rm digital_agency_postgres_data 2>/dev/null || true

echo ""
echo "3️⃣ Rebuilding and starting..."
docker-compose up -d --build

echo ""
echo "⏳ Waiting for database initialization and seeding..."
sleep 15

echo ""
echo "✅ Done! Database updated with Trends support."
