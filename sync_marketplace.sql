
-- Standardize Marketplace Enums to Lowercase

-- 1. Ensure all lowercase values exist in Enum types
-- Note: ALTER TYPE ... ADD VALUE cannot be executed inside a multi-statement transaction block in some Postgres versions.
-- We run these individually.

ALTER TYPE verificationstatusdb ADD VALUE IF NOT EXISTS 'pending';
ALTER TYPE verificationstatusdb ADD VALUE IF NOT EXISTS 'approved';
ALTER TYPE verificationstatusdb ADD VALUE IF NOT EXISTS 'rejected';

ALTER TYPE platformtypedb ADD VALUE IF NOT EXISTS 'instagram';
ALTER TYPE platformtypedb ADD VALUE IF NOT EXISTS 'tiktok';
ALTER TYPE platformtypedb ADD VALUE IF NOT EXISTS 'youtube';
ALTER TYPE platformtypedb ADD VALUE IF NOT EXISTS 'twitter';
ALTER TYPE platformtypedb ADD VALUE IF NOT EXISTS 'multi';

ALTER TYPE packagestatusdb ADD VALUE IF NOT EXISTS 'active';
ALTER TYPE packagestatusdb ADD VALUE IF NOT EXISTS 'paused';
ALTER TYPE packagestatusdb ADD VALUE IF NOT EXISTS 'deleted';

ALTER TYPE paymentmethodtype ADD VALUE IF NOT EXISTS 'mpesa';
ALTER TYPE paymentmethodtype ADD VALUE IF NOT EXISTS 'airtel_money';
ALTER TYPE paymentmethodtype ADD VALUE IF NOT EXISTS 'bank_transfer';

ALTER TYPE wallettransactiontypedb ADD VALUE IF NOT EXISTS 'deposit';
ALTER TYPE wallettransactiontypedb ADD VALUE IF NOT EXISTS 'withdrawal';
ALTER TYPE wallettransactiontypedb ADD VALUE IF NOT EXISTS 'escrow_lock';
ALTER TYPE wallettransactiontypedb ADD VALUE IF NOT EXISTS 'escrow_release';
ALTER TYPE wallettransactiontypedb ADD VALUE IF NOT EXISTS 'escrow_refund';
ALTER TYPE wallettransactiontypedb ADD VALUE IF NOT EXISTS 'platform_fee';
ALTER TYPE wallettransactiontypedb ADD VALUE IF NOT EXISTS 'transfer';

ALTER TYPE wallettransactionstatusdb ADD VALUE IF NOT EXISTS 'pending';
ALTER TYPE wallettransactionstatusdb ADD VALUE IF NOT EXISTS 'processing';
ALTER TYPE wallettransactionstatusdb ADD VALUE IF NOT EXISTS 'completed';
ALTER TYPE wallettransactionstatusdb ADD VALUE IF NOT EXISTS 'failed';
ALTER TYPE wallettransactionstatusdb ADD VALUE IF NOT EXISTS 'cancelled';

ALTER TYPE escrowstatusdb ADD VALUE IF NOT EXISTS 'locked';
ALTER TYPE escrowstatusdb ADD VALUE IF NOT EXISTS 'released';
ALTER TYPE escrowstatusdb ADD VALUE IF NOT EXISTS 'refunded';
ALTER TYPE escrowstatusdb ADD VALUE IF NOT EXISTS 'disputed';

ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'open';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'closed';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'pending';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'accepted';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'in_progress';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'draft_submitted';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'revision_requested';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'draft_approved';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'published';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'pending_review';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'completed';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'disputed';
ALTER TYPE campaignstatusdb ADD VALUE IF NOT EXISTS 'cancelled';

ALTER TYPE deliverablestatusdb ADD VALUE IF NOT EXISTS 'pending';
ALTER TYPE deliverablestatusdb ADD VALUE IF NOT EXISTS 'draft';
ALTER TYPE deliverablestatusdb ADD VALUE IF NOT EXISTS 'submitted';
ALTER TYPE deliverablestatusdb ADD VALUE IF NOT EXISTS 'approved';
ALTER TYPE deliverablestatusdb ADD VALUE IF NOT EXISTS 'rejected';
ALTER TYPE deliverablestatusdb ADD VALUE IF NOT EXISTS 'published';
ALTER TYPE deliverablestatusdb ADD VALUE IF NOT EXISTS 'verified';

ALTER TYPE disputestatusdb ADD VALUE IF NOT EXISTS 'open';
ALTER TYPE disputestatusdb ADD VALUE IF NOT EXISTS 'under_review';
ALTER TYPE disputestatusdb ADD VALUE IF NOT EXISTS 'resolved';
ALTER TYPE disputestatusdb ADD VALUE IF NOT EXISTS 'closed';

ALTER TYPE bidstatusdb ADD VALUE IF NOT EXISTS 'pending';
ALTER TYPE bidstatusdb ADD VALUE IF NOT EXISTS 'accepted';
ALTER TYPE bidstatusdb ADD VALUE IF NOT EXISTS 'rejected';
ALTER TYPE bidstatusdb ADD VALUE IF NOT EXISTS 'withdrawn';
ALTER TYPE bidstatusdb ADD VALUE IF NOT EXISTS 'completed';
ALTER TYPE bidstatusdb ADD VALUE IF NOT EXISTS 'paid';

ALTER TYPE proofofworkstatus ADD VALUE IF NOT EXISTS 'pending';
ALTER TYPE proofofworkstatus ADD VALUE IF NOT EXISTS 'approved';
ALTER TYPE proofofworkstatus ADD VALUE IF NOT EXISTS 'rejected';
ALTER TYPE proofofworkstatus ADD VALUE IF NOT EXISTS 'revision_requested';

ALTER TYPE campaigncontentstatus ADD VALUE IF NOT EXISTS 'draft';
ALTER TYPE campaigncontentstatus ADD VALUE IF NOT EXISTS 'submitted';
ALTER TYPE campaigncontentstatus ADD VALUE IF NOT EXISTS 'approved';
ALTER TYPE campaigncontentstatus ADD VALUE IF NOT EXISTS 'published';

-- 2. Update existing data to lowercase
DO $$
BEGIN
    -- Influencer Profiles
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'influencer_profiles') THEN
        UPDATE influencer_profiles SET verification_status = LOWER(verification_status::text)::verificationstatusdb 
        WHERE verification_status::text != LOWER(verification_status::text);
    END IF;
    
    -- Bids
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'bids') THEN
        UPDATE bids SET status = LOWER(status::text)::bidstatusdb 
        WHERE status::text != LOWER(status::text);
    END IF;

    -- Campaigns
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'campaigns') THEN
        UPDATE campaigns SET status = LOWER(status::text)::campaignstatusdb 
        WHERE status::text != LOWER(status::text);
    END IF;

    -- Deliverables
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'deliverables') THEN
        UPDATE deliverables SET status = LOWER(status::text)::deliverablestatusdb 
        WHERE status::text != LOWER(status::text);
        
        UPDATE deliverables SET platform = LOWER(platform::text)::platformtypedb 
        WHERE platform::text != LOWER(platform::text);
    END IF;

    -- Packages
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'packages') THEN
        UPDATE packages SET status = LOWER(status::text)::packagestatusdb 
        WHERE status::text != LOWER(status::text);
        
        UPDATE packages SET platform = LOWER(platform::text)::platformtypedb 
        WHERE platform::text != LOWER(platform::text);
    END IF;

    -- Wallet Transactions
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'wallet_transactions') THEN
        UPDATE wallet_transactions SET transaction_type = LOWER(transaction_type::text)::wallettransactiontypedb 
        WHERE transaction_type::text != LOWER(transaction_type::text);
        
        UPDATE wallet_transactions SET status = LOWER(status::text)::wallettransactionstatusdb 
        WHERE status::text != LOWER(status::text);
    END IF;

    -- Escrow Holds
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'escrow_holds') THEN
        UPDATE escrow_holds SET status = LOWER(status::text)::escrowstatusdb 
        WHERE status::text != LOWER(status::text);
    END IF;

    -- Disputes
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'disputes') THEN
        UPDATE disputes SET status = LOWER(status::text)::disputestatusdb 
        WHERE status::text != LOWER(status::text);
    END IF;
    
    -- Proof of Work
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'proof_of_work') THEN
        UPDATE proof_of_work SET status = LOWER(status::text)::proofofworkstatus 
        WHERE status::text != LOWER(status::text);
    END IF;
    
    -- Campaign Content
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'campaign_content') THEN
        UPDATE campaign_content SET status = LOWER(status::text)::campaigncontentstatus 
        WHERE status::text != LOWER(status::text);
    END IF;
END $$;
