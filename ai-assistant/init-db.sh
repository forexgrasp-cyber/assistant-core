#!/bin/bash
# Initialize Unified Platform Database
# Creates tables for multi-tenant capability management

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- TENANTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    billing_email VARCHAR(255),
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    trial_ends_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_email ON tenants(email);
CREATE INDEX idx_tenants_status ON tenants(status);

-- ============================================================
-- TENANT ENTITLEMENTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS tenant_entitlements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    capability VARCHAR(100) NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID REFERENCES tenants(id),
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    UNIQUE(tenant_id, capability)
);

CREATE INDEX idx_tenant_entitlements_tenant ON tenant_entitlements(tenant_id);
CREATE INDEX idx_tenant_entitlements_capability ON tenant_entitlements(capability);

-- ============================================================
-- PRODUCT BUNDLES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS product_bundles (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    tagline VARCHAR(255),
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(50),
    monthly_price_cents INTEGER NOT NULL DEFAULT 0,
    annual_price_cents INTEGER NOT NULL DEFAULT 0,
    capabilities TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TENANT SUBSCRIPTIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS tenant_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_bundle_id VARCHAR(50) NOT NULL REFERENCES product_bundles(id),
    status VARCHAR(50) DEFAULT 'active',
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    current_period_start TIMESTAMPTZ DEFAULT NOW(),
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT false,
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenant_subscriptions_tenant ON tenant_subscriptions(tenant_id);
CREATE INDEX idx_tenant_subscriptions_status ON tenant_subscriptions(status);

-- ============================================================
-- CONVERSATION HISTORY TABLE (Shared across products)
-- ============================================================
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    product_type VARCHAR(50) NOT NULL, -- callagent, tutor, jarvis, hvac
    user_id VARCHAR(255),
    channel VARCHAR(50), -- voice, chat, sms, email
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}'
);

CREATE INDEX idx_conversation_tenant ON conversation_history(tenant_id);
CREATE INDEX idx_conversation_session ON conversation_history(session_id);
CREATE INDEX idx_conversation_user ON conversation_history(user_id);
CREATE INDEX idx_conversation_started ON conversation_history(started_at DESC);

-- ============================================================
-- CONVERSATION MESSAGES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversation_history(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text', -- text, audio, mixed
    metadata JSONB DEFAULT '{}',
    tokens_used INTEGER,
    cost_cents INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON conversation_messages(conversation_id);
CREATE INDEX idx_messages_created ON conversation_messages(created_at);

-- ============================================================
-- TUTOR-SPECIFIC TABLES
-- ============================================================
CREATE TABLE IF NOT EXISTS learner_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    native_language VARCHAR(10) NOT NULL DEFAULT 'en',
    target_language VARCHAR(10) NOT NULL DEFAULT 'es',
    cefr_level VARCHAR(10) NOT NULL DEFAULT 'A1',
    learning_goals TEXT[],
    preferred_topics TEXT[],
    study_time_minutes_per_day INTEGER DEFAULT 15,
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, user_id)
);

CREATE INDEX idx_learner_profiles_tenant ON learner_profiles(tenant_id);
CREATE INDEX idx_learner_profiles_user ON learner_profiles(user_id);

CREATE TABLE IF NOT EXISTS study_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    learner_profile_id UUID NOT NULL REFERENCES learner_profiles(id) ON DELETE CASCADE,
    name VARCHAR(255),
    target_cefr_level VARCHAR(10),
    estimated_weeks INTEGER,
    weekly_hours DECIMAL(4,2),
    focus_areas TEXT[],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    learner_profile_id UUID NOT NULL REFERENCES learner_profiles(id) ON DELETE CASCADE,
    lesson_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'not_started', -- not_started, in_progress, completed, mastered
    score DECIMAL(5,2),
    attempts INTEGER DEFAULT 0,
    time_spent_seconds INTEGER DEFAULT 0,
    completed_at TIMESTAMPTZ,
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, learner_profile_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS vocabulary_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    learner_profile_id UUID NOT NULL REFERENCES learner_profiles(id) ON DELETE CASCADE,
    word VARCHAR(255) NOT NULL,
    translation VARCHAR(255),
    language VARCHAR(10),
    mastery_level DECIMAL(3,2) DEFAULT 0,
    last_reviewed TIMESTAMPTZ,
    next_review TIMESTAMPTZ,
    review_count INTEGER DEFAULT 0,
    ease_factor DECIMAL(3,2) DEFAULT 2.5
);

CREATE INDEX idx_vocab_learner ON vocabulary_progress(learner_profile_id);
CREATE INDEX idx_vocab_next_review ON vocabulary_progress(next_review);

-- ============================================================
-- CALLAGENT-SPECIFIC TABLES
-- ============================================================
CREATE TABLE IF NOT EXISTS call_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    call_sid VARCHAR(255),
    direction VARCHAR(20), -- inbound, outbound
    from_number VARCHAR(50),
    to_number VARCHAR(50),
    status VARCHAR(50),
    duration_seconds INTEGER,
    recording_url TEXT,
    transcription_text TEXT,
    cost_cents INTEGER,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_calls_tenant ON call_records(tenant_id);
CREATE INDEX idx_calls_sid ON call_records(call_sid);
CREATE INDEX idx_calls_started ON call_records(started_at DESC);

-- ============================================================
-- JARVIS-SPECIFIC TABLES
-- ============================================================
CREATE TABLE IF NOT EXISTS jarvis_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    due_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    source VARCHAR(50), -- email, chat, voice, manual
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jarvis_tasks_tenant ON jarvis_tasks(tenant_id);
CREATE INDEX idx_jarvis_tasks_user ON jarvis_tasks(user_id);
CREATE INDEX idx_jarvis_tasks_status ON jarvis_tasks(status);

-- ============================================================
-- HVAC-SPECIFIC TABLES
-- ============================================================
CREATE TABLE IF NOT EXISTS hvac_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50),
    customer_email VARCHAR(255),
    address TEXT,
    issue_type VARCHAR(50), -- emergency, maintenance, install, repair
    priority VARCHAR(20) DEFAULT 'normal',
    status VARCHAR(50) DEFAULT 'open',
    assigned_technician_id UUID,
    scheduled_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    description TEXT,
    parts_needed TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hvac_tickets_tenant ON hvac_tickets(tenant_id);
CREATE INDEX idx_hvac_tickets_status ON hvac_tickets(status);
CREATE INDEX idx_hvac_tickets_scheduled ON hvac_tickets(scheduled_at);

-- ============================================================
-- AUDIT LOG TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- ============================================================
-- INSERT DEFAULT PRODUCT BUNDLES
-- ============================================================
INSERT INTO product_bundles (id, name, tagline, description, icon, color, monthly_price_cents, annual_price_cents, capabilities, sort_order) VALUES
(
    'callagent',
    'CallAgent',
    'AI Voice Receptionist',
    'Never miss a call. AI handles inbound/outbound, books appointments, qualifies leads, transfers to humans.',
    'phone',
    'blue',
    4900,
    47040,
    ARRAY[
        'voice.inbound','voice.outbound','voice.tts.standard','voice.stt.standard',
        'voice.telephony.twilio','voice.telephony.plivo','voice.recording','voice.transcription','voice.vad',
        'intelligence.llm.standard','intelligence.llm.byok','intelligence.memory.short',
        'integration.crm','integration.sms','integration.webhooks','integration.api',
        'platform.tenants','platform.rbac','platform.analytics','platform.export'
    ],
    1
),
(
    'tutor',
    'Language Tutor',
    'AI Language Coach',
    'Learn 70 languages with AI. Pronunciation scoring, writing correction, personalized curriculum, gamified progress.',
    'book',
    'purple',
    2900,
    27840,
    ARRAY[
        'tutor.curriculum','tutor.memory','tutor.gamification','tutor.pronunciation','tutor.writing',
        'tutor.conversation','tutor.lesson_gen','tutor.voice_selection','tutor.offline',
        'voice.tts.standard','voice.tts.premium','voice.stt.standard','voice.vad',
        'intelligence.llm.standard','intelligence.llm.byok','intelligence.memory.short','intelligence.memory.long',
        'integration.webhooks','integration.api',
        'platform.tenants','platform.rbac','platform.analytics','platform.export'
    ],
    2
),
(
    'jarvis',
    'Jarvis',
    'AI Chief of Staff',
    'Your AI executive assistant. Email, calendar, tasks, research, workflows - proactive and autonomous.',
    'brain',
    'amber',
    7900,
    75840,
    ARRAY[
        'intelligence.llm.premium','intelligence.llm.byok','intelligence.rag.basic','intelligence.rag.advanced',
        'intelligence.tools.basic','intelligence.tools.advanced','intelligence.memory.short','intelligence.memory.long',
        'intelligence.reasoning',
        'integration.email','integration.calendar','integration.slack','integration.webhooks','integration.api',
        'platform.tenants','platform.rbac','platform.analytics','platform.export','platform.workflows'
    ],
    3
),
(
    'hvac',
    'HVAC Specialist',
    'Vertical Receptionist',
    'HVAC-specific: emergency dispatch, maintenance scheduling, parts lookup, technician routing.',
    'wrench',
    'green',
    9900,
    95040,
    ARRAY[
        'voice.inbound','voice.outbound','voice.tts.standard','voice.stt.standard',
        'voice.telephony.twilio','voice.recording','voice.transcription','voice.vad',
        'intelligence.llm.standard','intelligence.llm.byok','intelligence.memory.short',
        'integration.crm','integration.sms','integration.webhooks','integration.api',
        'platform.tenants','platform.rbac','platform.analytics','platform.export'
    ],
    4
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    tagline = EXCLUDED.tagline,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    monthly_price_cents = EXCLUDED.monthly_price_cents,
    annual_price_cents = EXCLUDED.annual_price_cents,
    capabilities = EXCLUDED.capabilities,
    updated_at = NOW();

-- ============================================================
-- INSERT DEMO TENANTS
-- ============================================================
INSERT INTO tenants (id, name, slug, email, status) VALUES
    ('11111111-1111-1111-1111-111111111111', 'CallAgent Demo', 'callagent-demo', 'demo@callagent.example.com', 'active'),
    ('22222222-2222-2222-2222-222222222222', 'Tutor Demo', 'tutor-demo', 'demo@tutor.example.com', 'active'),
    ('33333333-3333-3333-3333-333333333333', 'Jarvis Demo', 'jarvis-demo', 'demo@jarvis.example.com', 'active'),
    ('44444444-4444-4444-4444-444444444444', 'HVAC Demo', 'hvac-demo', 'demo@hvac.example.com', 'active'),
    ('55555555-5555-5555-5555-555555555555', 'Combo Demo', 'combo-demo', 'demo@combo.example.com', 'active')
ON CONFLICT (id) DO NOTHING;

-- Grant entitlements to demo tenants
-- CallAgent Demo
INSERT INTO tenant_entitlements (tenant_id, capability) 
SELECT '11111111-1111-1111-1111-111111111111', unnest(capabilities) FROM product_bundles WHERE id = 'callagent'
ON CONFLICT DO NOTHING;

-- Tutor Demo
INSERT INTO tenant_entitlements (tenant_id, capability) 
SELECT '22222222-2222-2222-2222-222222222222', unnest(capabilities) FROM product_bundles WHERE id = 'tutor'
ON CONFLICT DO NOTHING;

-- Jarvis Demo
INSERT INTO tenant_entitlements (tenant_id, capability) 
SELECT '33333333-3333-3333-3333-333333333333', unnest(capabilities) FROM product_bundles WHERE id = 'jarvis'
ON CONFLICT DO NOTHING;

-- HVAC Demo
INSERT INTO tenant_entitlements (tenant_id, capability) 
SELECT '44444444-4444-4444-4444-444444444444', unnest(capabilities) FROM product_bundles WHERE id = 'hvac'
ON CONFLICT DO NOTHING;

-- Combo Demo (all capabilities)
INSERT INTO tenant_entitlements (tenant_id, capability)
SELECT '55555555-5555-5555-5555-555555555555', c.value 
FROM (SELECT unnest(enum_range(NULL::capability_enum)) as value) c
ON CONFLICT DO NOTHING;

-- Insert subscriptions
INSERT INTO tenant_subscriptions (tenant_id, product_bundle_id, status, current_period_end) VALUES
    ('11111111-1111-1111-1111-111111111111', 'callagent', 'active', NOW() + INTERVAL '1 month'),
    ('22222222-2222-2222-2222-222222222222', 'tutor', 'active', NOW() + INTERVAL '1 month'),
    ('33333333-3333-3333-3333-333333333333', 'jarvis', 'active', NOW() + INTERVAL '1 month'),
    ('44444444-4444-4444-4444-444444444444', 'hvac', 'active', NOW() + INTERVAL '1 month'),
    ('55555555-5555-5555-5555-555555555555', 'callagent', 'active', NOW() + INTERVAL '1 month'),
    ('55555555-5555-5555-5555-555555555555', 'tutor', 'active', NOW() + INTERVAL '1 month'),
    ('55555555-5555-5555-5555-555555555555', 'jarvis', 'active', NOW() + INTERVAL '1 month'),
    ('55555555-5555-5555-5555-555555555555', 'hvac', 'active', NOW() + INTERVAL '1 month')
ON CONFLICT DO NOTHING;

EOSQL

echo "✅ Unified platform database initialized successfully!"