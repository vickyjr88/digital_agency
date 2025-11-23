# Quick Fix Guide: Database Connection Issue

## Problem
The API container cannot connect to PostgreSQL because it's trying to connect to `localhost:5432`, but from inside Docker, `localhost` refers to the container itself, not the host machine.

## Solution
Changed database host from `localhost` to `host.docker.internal` which is Docker's special DNS name for accessing the host machine from inside containers.

## Files Updated
1. `database/config.py` - Changed default DATABASE_URL
2. `.env.example` - Updated with correct host

## What You Need to Do

### Option 1: Update .env file manually
Open `.env` and change:
```
FROM: DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dexter
TO:   DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/dexter
```

### Option 2: Recreate .env from example
```bash
cp .env.example .env
# Then add your actual API keys
```

## Then Restart the API Container
```bash
docker-compose restart agency-api
```

## Verify It Works
```bash
# Check logs
docker logs agency-api --tail 20

# Test registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User"
  }'
```

## Why This Happens
- **Inside Docker container**: `localhost` = the container itself
- **On host machine**: `localhost` = your Mac
- **Solution**: Use `host.docker.internal` to access host from container

## Alternative: Run PostgreSQL in Docker
If you want everything in Docker, you could add a PostgreSQL service to docker-compose.yml, but since you already have one running on the host, using `host.docker.internal` is simpler.

---
**Status**: Code fixed, needs .env update and container restart
