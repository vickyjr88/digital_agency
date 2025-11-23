# SaaS Transformation Plan: Dexter - AI Content Marketing Platform

## Executive Summary

Transform the current static "Digital Employee" bot into **Dexter**, a multi-tenant SaaS platform that enables businesses to automatically generate trending, brand-relevant social media content. Users can sign up, define their brands, and receive AI-generated content tailored to current trends.

---

## 1. Product Vision

**Dexter** - Your AI Content Marketing Assistant

**Tagline:** "Never miss a trend. Never run out of content."

**Value Proposition:**
- Automatically detects trending topics relevant to your industry
- Generates multi-platform content (Twitter, Facebook, Instagram, TikTok) in your brand voice
- Human-in-the-loop approval workflow
- Schedule and publish directly to social platforms (future)

---

## 2. Core Features & Pricing Tiers

### 2.1 Free Tier (Freemium)
**Price:** $0/month
**Limits:**
- 1 brand profile
- 10 content pieces per month
- Manual trend selection only
- 7-day content history
- Watermark on generated content ("Powered by Dexter")

**Features:**
- Basic brand profile setup (name, industry, voice)
- Manual content generation
- Content preview and editing
- Copy-to-clipboard functionality

---

### 2.2 Starter Tier
**Price:** $29/month
**Limits:**
- 3 brand profiles
- 100 content pieces per month
- AI trend detection (daily)
- 30-day content history
- No watermark

**Features:**
- Everything in Free
- Automated daily content generation
- Basic analytics (views, engagement tracking)
- Email notifications for new content
- Custom hashtag sets per brand
- Export to CSV

---

### 2.3 Professional Tier
**Price:** $99/month
**Limits:**
- 10 brand profiles
- 500 content pieces per month
- AI trend detection (3x daily)
- 90-day content history
- Priority AI processing

**Features:**
- Everything in Starter
- Advanced brand voice customization (tone, style, language)
- Content calendar view
- Team collaboration (3 team members)
- Webhook integrations
- API access (basic)
- Advanced analytics dashboard
- Content performance insights

---

### 2.4 Agency Tier
**Price:** $299/month
**Limits:**
- Unlimited brand profiles
- 2,000 content pieces per month
- AI trend detection (hourly)
- Unlimited content history
- White-label option

**Features:**
- Everything in Professional
- Client management dashboard
- Unlimited team members
- Full API access
- Custom AI model fine-tuning
- Dedicated account manager
- Priority support (24/7)
- Direct social media publishing (Twitter, Facebook, LinkedIn)
- Custom integrations

---

## 3. Technical Architecture

### 3.1 Database Schema

**Users Table**
```sql
- id (UUID, PK)
- email (unique)
- password_hash
- name
- subscription_tier (free/starter/pro/agency)
- subscription_status (active/cancelled/expired)
- stripe_customer_id
- created_at
- updated_at
```

**Brands Table**
```sql
- id (UUID, PK)
- user_id (FK -> Users)
- name
- industry
- description
- voice (casual/professional/humorous/etc)
- content_focus (JSON array)
- hashtags (JSON array)
- custom_instructions (text)
- logo_url
- created_at
- updated_at
```

**Content Table**
```sql
- id (UUID, PK)
- brand_id (FK -> Brands)
- trend
- trend_category (viral/local/niche)
- tweet
- facebook_post
- instagram_reel_script (JSON)
- tiktok_idea (JSON)
- status (pending/approved/rejected/published)
- generated_at
- approved_at
- published_at
- metadata (JSON - analytics, engagement)
```

**Usage Table** (for billing)
```sql
- id (UUID, PK)
- user_id (FK -> Users)
- month (YYYY-MM)
- content_generated_count
- api_calls_count
- updated_at
```

**Teams Table** (for collaboration)
```sql
- id (UUID, PK)
- user_id (FK -> Users, owner)
- brand_id (FK -> Brands)
- member_email
- role (viewer/editor/admin)
- invited_at
- accepted_at
```

---

### 3.2 Technology Stack

**Backend:**
- **Framework:** FastAPI (Python) - current
- **Database:** PostgreSQL (replace Google Sheets)
- **ORM:** SQLAlchemy
- **Authentication:** JWT tokens + OAuth2
- **Payment:** Stripe API
- **Email:** SendGrid or AWS SES
- **Task Queue:** Celery + Redis (for async content generation)
- **Storage:** AWS S3 (for logos, media)

**Frontend:**
- **Framework:** React (current) + TypeScript
- **Routing:** React Router (current)
- **State Management:** Zustand or React Query
- **UI:** Tailwind CSS (current) + shadcn/ui
- **Forms:** React Hook Form + Zod validation
- **Charts:** Recharts or Chart.js

**Infrastructure:**
- **Hosting:** AWS (EC2/ECS) or Railway/Render
- **CDN:** CloudFront or Cloudflare
- **Monitoring:** Sentry + LogRocket
- **Analytics:** PostHog or Mixpanel

---

## 4. Implementation Phases

### Phase 1: Foundation (Weeks 1-3)
**Goal:** Multi-tenancy + User Authentication

**Tasks:**
1. Set up PostgreSQL database
2. Create database schema and migrations (Alembic)
3. Implement user registration/login (JWT)
4. Build user dashboard (brand list, usage stats)
5. Migrate from Google Sheets to PostgreSQL
6. Add brand CRUD operations
7. Update content generation to be brand-specific

**Deliverables:**
- Users can sign up and log in
- Users can create/edit/delete brands
- Content is stored per user/brand in PostgreSQL

---

### Phase 2: Billing & Subscriptions (Weeks 4-5)
**Goal:** Monetization infrastructure

**Tasks:**
1. Integrate Stripe for payments
2. Create subscription management UI
3. Implement usage tracking and limits
4. Build pricing page
5. Add subscription upgrade/downgrade flows
6. Implement trial period (14 days)
7. Email notifications for billing events

**Deliverables:**
- Users can subscribe to paid plans
- Usage limits are enforced
- Stripe webhooks handle subscription events

---

### Phase 3: Enhanced Features (Weeks 6-8)
**Goal:** Differentiate paid tiers

**Tasks:**
1. Build content calendar view
2. Add analytics dashboard (content performance)
3. Implement team collaboration (invite members)
4. Create API endpoints for external integrations
5. Add webhook support
6. Build export functionality (CSV, PDF)
7. Implement email notifications for new content

**Deliverables:**
- Professional tier features are functional
- Users can collaborate on brands
- API documentation is available

---

### Phase 4: Automation & Scheduling (Weeks 9-10)
**Goal:** Automated content generation

**Tasks:**
1. Set up Celery task queue
2. Implement scheduled content generation (cron jobs)
3. Add trend detection frequency controls
4. Build content approval workflow
5. Email/Slack notifications for new content
6. Auto-publish to social media (Twitter API, Facebook Graph API)

**Deliverables:**
- Content is generated automatically based on tier
- Users receive notifications
- Direct publishing works (optional feature)

---

### Phase 5: Polish & Launch (Weeks 11-12)
**Goal:** Production-ready SaaS

**Tasks:**
1. Comprehensive testing (unit, integration, E2E)
2. Performance optimization
3. Security audit
4. Create onboarding flow (product tour)
5. Build landing page + marketing site
6. Set up monitoring and error tracking
7. Beta launch with early users
8. Gather feedback and iterate

**Deliverables:**
- Production-ready application
- Landing page live
- Beta users onboarded

---

## 5. Billable Features Breakdown

### Content Generation Credits
- **Free:** 10/month
- **Starter:** 100/month
- **Pro:** 500/month
- **Agency:** 2,000/month
- **Overage:** $0.50 per additional content piece

### API Calls (for integrations)
- **Free:** None
- **Starter:** None
- **Pro:** 1,000/month
- **Agency:** 10,000/month
- **Overage:** $0.01 per call

### Team Members
- **Free:** 1 (owner only)
- **Starter:** 1 (owner only)
- **Pro:** 3 members
- **Agency:** Unlimited
- **Add-on:** $10/month per additional member (Pro tier)

### White-Label (Agency only)
- Remove "Powered by Dexter" branding
- Custom domain support
- Custom email templates

### Priority Support
- **Free/Starter:** Community support (Discord/Forum)
- **Pro:** Email support (48h response)
- **Agency:** 24/7 priority support + dedicated Slack channel

---

## 6. Revenue Projections (Year 1)

**Assumptions:**
- 1,000 sign-ups in first 6 months
- 10% conversion to paid (100 paid users)
- Average tier: Starter ($29/month)

**Monthly Recurring Revenue (MRR):**
- Free users: 900 × $0 = $0
- Starter: 60 × $29 = $1,740
- Pro: 30 × $99 = $2,970
- Agency: 10 × $299 = $2,990
- **Total MRR:** $7,700

**Annual Recurring Revenue (ARR):** $92,400

**With growth (20% MoM):**
- Month 6: $7,700
- Month 12: ~$19,000 MRR = $228,000 ARR

---

## 7. Marketing & Go-to-Market Strategy

### Target Audience
1. **Small businesses** (1-10 employees) - Starter tier
2. **Marketing agencies** - Agency tier
3. **Solopreneurs/Creators** - Free/Starter tier
4. **Startups** - Pro tier

### Marketing Channels
1. **Content Marketing:** Blog posts on AI, social media trends, content marketing
2. **SEO:** Target keywords like "AI content generator", "social media automation"
3. **Social Media:** Twitter, LinkedIn (showcase generated content)
4. **Product Hunt:** Launch for visibility
5. **Affiliate Program:** 20% recurring commission
6. **Partnerships:** Integrate with tools like Buffer, Hootsuite

### Launch Strategy
1. **Beta Launch:** 50 early adopters (free Pro tier for 3 months)
2. **Feedback Loop:** Weekly surveys, feature requests
3. **Public Launch:** Product Hunt, Hacker News, Reddit (r/SaaS, r/marketing)
4. **Referral Program:** Give 1 month free for each referral

---

## 8. Key Metrics to Track

### Product Metrics
- **Sign-ups:** Daily/weekly/monthly
- **Activation Rate:** % of users who create their first brand
- **Content Generation Rate:** Avg content pieces per user
- **Approval Rate:** % of generated content approved by users
- **Churn Rate:** Monthly subscription cancellations

### Business Metrics
- **MRR/ARR:** Monthly/Annual Recurring Revenue
- **Customer Acquisition Cost (CAC)**
- **Lifetime Value (LTV)**
- **LTV:CAC Ratio** (target: 3:1)
- **Net Revenue Retention (NRR)**

### Engagement Metrics
- **Daily Active Users (DAU)**
- **Content Edits:** How often users edit generated content
- **API Usage:** For Pro/Agency tiers
- **Team Collaboration:** Invites sent, accepted

---

## 9. Risk Mitigation

### Technical Risks
- **AI API Costs:** Monitor Gemini API usage, implement caching
- **Scalability:** Use load balancers, auto-scaling (AWS ECS)
- **Data Loss:** Daily backups, point-in-time recovery

### Business Risks
- **Low Conversion:** Offer better free tier, improve onboarding
- **High Churn:** Improve content quality, add more value
- **Competition:** Focus on niche (Kenya/Africa trends), better UX

### Legal Risks
- **GDPR Compliance:** Implement data export, deletion
- **Terms of Service:** Clear usage policies
- **Content Liability:** Disclaimer that users are responsible for published content

---

## 10. Next Steps

### Immediate Actions (This Week)
1. ✅ Create this plan document
2. Set up PostgreSQL database (local + production)
3. Design database schema in detail
4. Create wireframes for new UI (brand management, billing)
5. Research Stripe integration best practices

### Short-term (Next 2 Weeks)
1. Implement user authentication (registration, login, JWT)
2. Build brand CRUD operations
3. Migrate content generation to be brand-specific
4. Create basic user dashboard

### Medium-term (Next Month)
1. Integrate Stripe for subscriptions
2. Implement usage tracking and limits
3. Build pricing page and subscription flows
4. Launch private beta with 10-20 users

---

## 11. Success Criteria

**3 Months:**
- 500 total sign-ups
- 50 paid subscribers
- $2,000 MRR
- 70% user activation rate

**6 Months:**
- 2,000 total sign-ups
- 200 paid subscribers
- $8,000 MRR
- Product-market fit validated

**12 Months:**
- 5,000 total sign-ups
- 500 paid subscribers
- $20,000 MRR
- Profitable (revenue > costs)

---

## Appendix A: Competitive Analysis

### Competitors
1. **Jasper.ai** - General AI writing, $39-$125/month
2. **Copy.ai** - Marketing copy, $49/month
3. **Lately.ai** - Social media content, $99/month
4. **Buffer/Hootsuite** - Scheduling, $15-$99/month

### Dexter's Differentiators
- **Trend-first approach:** Content is always relevant to current trends
- **Multi-platform:** One trend → 4 content formats
- **Kenya/Africa focus:** Local trend detection (niche advantage)
- **Affordable:** Lower price point for small businesses
- **Human-in-the-loop:** Approval workflow, not auto-posting (safer)

---

## Appendix B: Technical Debt to Address

1. Replace Google Sheets with PostgreSQL
2. Add proper error handling and logging
3. Implement rate limiting on API
4. Add comprehensive tests (unit, integration)
5. Set up CI/CD pipeline
6. Implement proper secrets management (AWS Secrets Manager)
7. Add database migrations (Alembic)
8. Optimize AI prompts for cost and quality

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-23  
**Author:** Dexter Team  
**Status:** Draft - Ready for Review
