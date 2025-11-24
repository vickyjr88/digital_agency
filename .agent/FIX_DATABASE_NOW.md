# CRITICAL: Update Your .env File

## The Problem
Your `.env` file still has the old `DATABASE_URL` pointing to `localhost` instead of the `postgres` service name.

## The Fix

**Open your `.env` file and change line 21 from:**
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dexter
```

**To:**
```
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/dexter
```

## Why This Matters
- Inside Docker containers, `localhost` refers to the container itself
- `postgres` is the service name from docker-compose.yml
- Docker's internal DNS resolves `postgres` to the PostgreSQL container's IP

## Complete Steps

### 1. Update .env
```bash
# Open .env and change DATABASE_URL to:
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/dexter
```

### 2. Restart Services
```bash
docker-compose down
docker-compose up -d
```

### 3. Test Connection
```bash
# From inside the API container
docker exec -it agency-api python test_db_connection.py

# Or check logs
docker logs agency-api --tail 30
docker logs dexter-db --tail 20
```

### 4. Verify PostgreSQL is Running
```bash
docker ps | grep dexter-db
# Should show: dexter-db ... Up ... 0.0.0.0:5437->5432/tcp
```

## What I Changed

1. **docker-compose.yml**:
   - Added `dexter-network` for explicit service communication
   - All services now on the same network
   - Health checks ensure postgres is ready before API starts

2. **test_db_connection.py**:
   - New script to test database connectivity
   - Run it to verify connection works

## Expected .env Content
```env
# Database Configuration
# 'postgres' is the service name from docker-compose.yml
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/dexter

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here

# Other variables...
```

## Quick Test
After updating .env and restarting:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User"
  }'
```

Should return a JWT token instead of 500 error!

---
**Action Required**: Update DATABASE_URL in your .env file to use `postgres` instead of `localhost`
