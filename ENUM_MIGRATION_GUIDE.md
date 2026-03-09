# Enum Values Migration Guide

## Overview

This guide explains how to migrate UserRole and UserType enum values from UPPERCASE to lowercase in the production database.

### What Changed?

**Before (UPPERCASE):**
```python
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"

class UserType(str, enum.Enum):
    BRAND = "BRAND"
    INFLUENCER = "INFLUENCER"
    ADMIN = "ADMIN"
```

**After (lowercase):**
```python
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class UserType(str, enum.Enum):
    BRAND = "brand"
    INFLUENCER = "influencer"
    ADMIN = "admin"
```

### Why This Change?

The database already contained lowercase values (like `"brand"`, `"influencer"`) from earlier migrations, but the code expected UPPERCASE values. This caused errors like:

```
LookupError: 'brand' is not among the defined enum values. Enum name: usertype.
Possible values: BRAND, INFLUENCER, ADMIN
```

## Migration Scripts

### 1. `verify_enum_values.py`
**Purpose:** Check current state of enum values without making changes
**Safe to run:** ✅ Yes (read-only)
**When to use:** Before and after migration to verify state

### 2. `backup_database.sh`
**Purpose:** Create a database backup before migration
**Safe to run:** ✅ Yes (backup only)
**When to use:** REQUIRED before running migration

### 3. `migrate_enum_values.py`
**Purpose:** Convert UPPERCASE enum values to lowercase
**Safe to run:** ⚠️  Only after backup
**When to use:** After verifying current state and creating backup

### 4. `rollback_enum_migration.py`
**Purpose:** Revert lowercase values back to UPPERCASE (emergency use)
**Safe to run:** ⚠️  Only if migration fails
**When to use:** If migration causes issues and you need to rollback

## Step-by-Step Migration Process

### Phase 1: Preparation (On Production Server)

#### Step 1: SSH into Production Server
```bash
ssh root@164.68.99.36
cd /root/dexter-platform
```

#### Step 2: Verify Current State
```bash
# Enter the backend container
docker exec -it dexter-backend bash

# Run verification script
cd /app
python verify_enum_values.py
```

**Expected Output:**
```
⚠️  UPPERCASE enum values detected!
   Your code expects: lowercase values
   Action required: Run migration script
```

#### Step 3: Create Database Backup
```bash
# Exit container first
exit

# Run backup script
cd backend_dexter
chmod +x backup_database.sh
./backup_database.sh
```

**Verify backup was created:**
```bash
ls -lh backups/
# Should show: dexter_db_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Phase 2: Code Deployment

#### Step 4: Update Code on Server
```bash
# From your local machine
cd /Users/vickyjunior/projects/vdm/digital_agency
./deploy-dexter.sh
```

⚠️ **IMPORTANT:** After deployment, the application will still have errors until you run the migration script in Phase 3.

### Phase 3: Database Migration

#### Step 5: Run Migration Script
```bash
# SSH into server
ssh root@164.68.99.36
cd /root/dexter-platform

# Enter backend container
docker exec -it dexter-backend bash

# Run migration
cd /app
python migrate_enum_values.py
```

**Follow the prompts:**
1. Review current data state
2. Type `yes` when asked to confirm
3. Wait for migration to complete

**Expected Output:**
```
✅ Migration completed successfully!

Total records updated:
  UserRole: X
  UserType: Y

All enum values are now lowercase!
```

#### Step 6: Verify Migration Success
```bash
# Still in the container
python verify_enum_values.py
```

**Expected Output:**
```
✅ All enum values are lowercase!
   Your code expects: lowercase values
   Status: Database and code are in sync ✓
```

#### Step 7: Exit Container & Restart Services
```bash
exit  # Exit container

# Restart services to ensure everything loads correctly
docker-compose -f docker-compose.dexter.yml restart backend
```

### Phase 4: Testing

#### Step 8: Test Registration Endpoint
```bash
# Test user registration
curl -X POST https://dexter-api.vitaldigitalmedia.net/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "name": "Test User",
    "user_type": "brand"
  }'
```

**Expected:** Should return access token without enum errors ✅

#### Step 9: Test Login & User Retrieval
```bash
# Test login
curl -X POST https://dexter-api.vitaldigitalmedia.net/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@dexter.com",
    "password": "your-admin-password"
  }'
```

**Expected:** Should return access token without enum errors ✅

#### Step 10: Monitor Logs
```bash
# Check for any enum-related errors
docker logs dexter-backend --tail 100 -f
```

**Look for:** No `LookupError` or enum-related exceptions ✅

## Rollback Procedure (Emergency Only)

If migration causes issues:

### Step 1: Immediately Run Rollback Script
```bash
docker exec -it dexter-backend bash
cd /app
python rollback_enum_migration.py
# Type 'yes' to confirm
```

### Step 2: Revert Code Changes
```bash
# On your local machine, revert the enum changes
cd /Users/vickyjunior/projects/vdm/digital_agency/dexter-platform/backend_dexter

# Revert the file changes (or use git)
git checkout database/models.py

# Redeploy old code
cd /Users/vickyjunior/projects/vdm/digital_agency
./deploy-dexter.sh
```

### Step 3: Verify Rollback
```bash
docker exec -it dexter-backend python verify_enum_values.py
```

## Post-Migration Checklist

- [ ] Backup created successfully
- [ ] Code deployed with lowercase enum definitions
- [ ] Migration script completed without errors
- [ ] Verification script shows all values are lowercase
- [ ] User registration works correctly
- [ ] User login works correctly
- [ ] Admin endpoints accessible
- [ ] No enum-related errors in logs for 24 hours
- [ ] Backup can be deleted after 1 week

## Troubleshooting

### Issue: "Database connection failed"
**Solution:** Check environment variables in Docker container:
```bash
docker exec -it dexter-backend env | grep DB_
```

### Issue: "Some uppercase values remain"
**Solution:** Run migration script again - it's idempotent and safe to re-run:
```bash
docker exec -it dexter-backend python migrate_enum_values.py
```

### Issue: "Migration completed but errors still occur"
**Solution:** Restart the backend service to reload enum definitions:
```bash
docker-compose -f docker-compose.dexter.yml restart backend
```

### Issue: "Need to restore from backup"
**Solution:**
```bash
# Decompress backup
cd /root/dexter-platform/backend_dexter/backups
gunzip dexter_db_backup_YYYYMMDD_HHMMSS.sql.gz

# Restore to database
docker exec -i dexter-postgres psql -U postgres dexter_db < dexter_db_backup_YYYYMMDD_HHMMSS.sql
```

## Files Created

- ✅ `verify_enum_values.py` - Verification script (read-only)
- ✅ `backup_database.sh` - Database backup script
- ✅ `migrate_enum_values.py` - Migration script
- ✅ `rollback_enum_migration.py` - Rollback script
- ✅ `ENUM_MIGRATION_GUIDE.md` - This guide

## Support

If you encounter any issues during migration:
1. Check the troubleshooting section above
2. Review the logs: `docker logs dexter-backend`
3. Verify database state: `python verify_enum_values.py`
4. If needed, use rollback script to revert changes

## Timeline

**Recommended migration window:** During low-traffic hours (e.g., 2 AM - 4 AM EAT)

**Estimated downtime:** 5-10 minutes

**Preparation time:** 15 minutes (reading guide, creating backup)

**Migration time:** 2-3 minutes

**Testing time:** 10 minutes

**Total:** ~30-45 minutes
