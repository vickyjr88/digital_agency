-- Fix UserType enum case to use uppercase values

-- Add uppercase enum values if they don't exist
DO $$
BEGIN
    -- Add BRAND if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'BRAND'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'usertype')
    ) THEN
        ALTER TYPE usertype ADD VALUE 'BRAND';
    END IF;

    -- Add INFLUENCER if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'INFLUENCER'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'usertype')
    ) THEN
        ALTER TYPE usertype ADD VALUE 'INFLUENCER';
    END IF;

    -- Add ADMIN if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'ADMIN'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'usertype')
    ) THEN
        ALTER TYPE usertype ADD VALUE 'ADMIN';
    END IF;
END$$;

-- Update all existing records to use uppercase values
UPDATE users SET user_type = 'BRAND' WHERE user_type = 'brand';
UPDATE users SET user_type = 'INFLUENCER' WHERE user_type = 'influencer';
UPDATE users SET user_type = 'ADMIN' WHERE user_type = 'admin';

-- Verify the changes
SELECT user_type, COUNT(*) as count
FROM users
GROUP BY user_type;
