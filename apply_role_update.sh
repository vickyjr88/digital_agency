#!/bin/bash

# Update Database Schema and Seed Admin

echo "🔄 Updating Database Schema..."
echo ""

# We need to recreate the database to add the new 'role' column
# Since we are in early dev, this is acceptable.
# If you want to keep data, we would need a migration script.

echo "⚠️  WARNING: This will RESET the database to add the new 'role' column."
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
echo "✅ Done! Admin user seeded."
echo "   Admin Email: admin@dexter.com (or value of ADMIN_USER)"
echo "   Admin Pass:  changeme (or value of ADMIN_PASS)"
echo ""
echo "   Login at: http://localhost:3000/login"
