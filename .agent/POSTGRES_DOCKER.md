# PostgreSQL Now in Docker! 🐘

## What Changed

Added PostgreSQL as a Docker service in `docker-compose.yml`. This is cleaner and more portable than using the host's PostgreSQL.

## Benefits
✅ Everything runs in Docker (no external dependencies)  
✅ Consistent across all environments  
✅ Automatic database creation  
✅ Health checks ensure DB is ready before API starts  
✅ Persistent data with Docker volume  

## Configuration

**PostgreSQL Service:**
- Container: `dexter-db`
- Port: `5437` (host) → `5432` (container)
- Database: `dexter` (auto-created)
- User: `postgres`
- Password: `postgres`
- Volume: `postgres_data` (persists data)

**Connection String:**
```
postgresql://postgres:postgres@postgres:5432/dexter
```

## How to Start

```bash
# Stop existing containers
docker-compose down

# Start everything (PostgreSQL will be created automatically)
docker-compose up -d

# Check if PostgreSQL is healthy
docker ps

# Check logs
docker logs dexter-db
docker logs agency-api
```

## Database Initialization

The database and tables will be created automatically when the API starts (via the startup event in `server.py`).

## Access PostgreSQL

**From host machine:**
```bash
# Using psql
psql -h localhost -p 5437 -U postgres -d dexter

# Using Docker exec
docker exec -it dexter-db psql -U postgres -d dexter
```

**From API container:**
```bash
docker exec -it agency-api python -c "from database.config import engine; print('Connected!' if engine else 'Failed')"
```

## Files Updated
1. `docker-compose.yml` - Added postgres service
2. `database/config.py` - Changed host to `postgres`
3. `.env.example` - Updated DATABASE_URL
4. `alembic.ini` - Updated connection string

## Next Steps

1. Update your `.env` file:
   ```bash
   cp .env.example .env
   # Add your API keys
   ```

2. Start the stack:
   ```bash
   docker-compose up -d
   ```

3. Test signup:
   ```
   http://localhost:3000/signup
   ```

---
**Status**: Ready to start with `docker-compose up -d`
