# Enum Migration - Quick Reference Card

## 🚀 Quick Start (Copy & Paste)

### On Production Server (164.68.99.36)

```bash
# 1. SSH into server
ssh root@164.68.99.36
cd /root/dexter-platform

# 2. Create backup (REQUIRED!)
cd backend_dexter
./backup_database.sh

# 3. Verify current state
docker exec -it dexter-backend python /app/verify_enum_values.py

# 4. Run migration
docker exec -it dexter-backend python /app/migrate_enum_values.py
# When prompted, type: yes

# 5. Verify success
docker exec -it dexter-backend python /app/verify_enum_values.py

# 6. Restart backend
docker-compose -f docker-compose.dexter.yml restart backend

# 7. Test registration
curl -X POST https://dexter-api.vitaldigitalmedia.net/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test12345","name":"Test"}'
```

## 📋 Commands Summary

| Command | Purpose | Safe? |
|---------|---------|-------|
| `verify_enum_values.py` | Check current enum values | ✅ Yes (read-only) |
| `backup_database.sh` | Create database backup | ✅ Yes (backup only) |
| `migrate_enum_values.py` | Migrate UPPERCASE → lowercase | ⚠️  After backup |
| `rollback_enum_migration.py` | Revert lowercase → UPPERCASE | ⚠️  Emergency only |

## ⚡ Emergency Rollback

```bash
# If migration causes issues:
docker exec -it dexter-backend python /app/rollback_enum_migration.py
# Type: yes

# Restart services
docker-compose -f docker-compose.dexter.yml restart
```

## ✅ Success Indicators

- ✅ Verification script shows "All enum values are lowercase!"
- ✅ No `LookupError` in logs
- ✅ User registration returns token
- ✅ User login works correctly

## ❌ Failure Indicators

- ❌ Migration script errors
- ❌ "brand is not among defined enum values" errors
- ❌ Registration/login returns 500 errors
- ❌ Verification shows mixed/UPPERCASE values

## 📞 Troubleshooting One-Liners

```bash
# Check logs for errors
docker logs dexter-backend --tail 50

# Check database connection
docker exec -it dexter-backend env | grep DB_

# Restart everything
docker-compose -f docker-compose.dexter.yml restart

# List backups
ls -lh backend_dexter/backups/
```

## 🕐 Recommended Migration Time

- **Best time:** 2 AM - 4 AM EAT (low traffic)
- **Duration:** ~10 minutes
- **Downtime:** ~5 minutes

## 📁 Files Reference

All scripts located in: `/root/dexter-platform/backend_dexter/`

- `verify_enum_values.py` - Verification
- `migrate_enum_values.py` - Migration
- `rollback_enum_migration.py` - Rollback
- `backup_database.sh` - Backup
- `ENUM_MIGRATION_GUIDE.md` - Full guide (read this first!)
- `MIGRATION_QUICK_REFERENCE.md` - This file

## 🎯 Migration Checklist

- [ ] Read ENUM_MIGRATION_GUIDE.md
- [ ] Schedule during low-traffic time
- [ ] SSH into production server
- [ ] Run backup_database.sh
- [ ] Verify backup file created
- [ ] Run verify_enum_values.py (before)
- [ ] Deploy updated code
- [ ] Run migrate_enum_values.py
- [ ] Run verify_enum_values.py (after)
- [ ] Restart backend service
- [ ] Test registration endpoint
- [ ] Test login endpoint
- [ ] Monitor logs for 30 minutes
- [ ] Keep backup for 1 week

## 💡 Pro Tips

1. **Always backup first** - No exceptions!
2. **Run verification before AND after** - Confirm success
3. **Test immediately after** - Don't wait to find issues
4. **Monitor logs** - Watch for 30 minutes post-migration
5. **Keep backup** - Don't delete for at least 1 week

---
**Need help?** Read the full guide: `ENUM_MIGRATION_GUIDE.md`
