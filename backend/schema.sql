-- ============================================
-- OPUS Phase 1: Database Schema Migration
-- Vendor Risk Assessment System
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Table: vendors
-- ============================================
CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    vendor_type VARCHAR(100),
    contract_value DECIMAL(15, 2),
    domain VARCHAR(255),
    contact_email VARCHAR(255),
    contact_name VARCHAR(255),
    industry VARCHAR(100),
    employee_count INTEGER,
    address TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Table: documents
-- ============================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    file_name VARCHAR(500) NOT NULL,
    file_path TEXT,
    file_type VARCHAR(50),
    file_size BIGINT,
    classification VARCHAR(100),
    classification_confidence DECIMAL(5, 4),
    extracted_text TEXT,
    extracted_metadata JSONB DEFAULT '{}',
    extracted_dates JSONB DEFAULT '{}',
    processing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Table: security_reviews
-- ============================================
CREATE TABLE IF NOT EXISTS security_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    overall_score DECIMAL(5, 2),
    grade VARCHAR(2),
    certificate_score DECIMAL(5, 2),
    domain_security_score DECIMAL(5, 2),
    breach_history_score DECIMAL(5, 2),
    questionnaire_score DECIMAL(5, 2),
    findings JSONB DEFAULT '[]',
    critical_issues JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    report JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Table: audit_logs
-- ============================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE SET NULL,
    agent_name VARCHAR(100) NOT NULL,
    action VARCHAR(255) NOT NULL,
    tool_name VARCHAR(100),
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'success',
    error_message TEXT,
    duration_ms INTEGER,
    token_usage JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Table: policies (for security policy RAG)
-- ============================================
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'security',
    content TEXT NOT NULL,
    summary TEXT,
    source VARCHAR(255),
    version VARCHAR(50),
    effective_date DATE,
    expiry_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Table: breaches (internal breach database)
-- ============================================
CREATE TABLE IF NOT EXISTS breaches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    breach_date DATE,
    records_exposed BIGINT,
    data_types TEXT[],
    severity VARCHAR(50),
    description TEXT,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Table: vendor_review_states
-- ============================================
CREATE TABLE IF NOT EXISTS vendor_review_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    state_data JSONB NOT NULL DEFAULT '{}',
    current_phase VARCHAR(100) DEFAULT 'intake',
    messages JSONB DEFAULT '[]',
    errors JSONB DEFAULT '[]',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Indexes
-- ============================================
CREATE INDEX IF NOT EXISTS idx_documents_vendor_id ON documents(vendor_id);
CREATE INDEX IF NOT EXISTS idx_documents_classification ON documents(classification);
CREATE INDEX IF NOT EXISTS idx_security_reviews_vendor_id ON security_reviews(vendor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_vendor_id ON audit_logs(vendor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_agent_name ON audit_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_policies_category ON policies(category);
CREATE INDEX IF NOT EXISTS idx_policies_is_active ON policies(is_active);
CREATE INDEX IF NOT EXISTS idx_breaches_company_name ON breaches(company_name);
CREATE INDEX IF NOT EXISTS idx_breaches_domain ON breaches(domain);
CREATE INDEX IF NOT EXISTS idx_vendor_review_states_vendor_id ON vendor_review_states(vendor_id);

-- ============================================
-- Row Level Security
-- ============================================
ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE breaches ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_review_states ENABLE ROW LEVEL SECURITY;

-- Permissive policies for service role access
CREATE POLICY "service_role_vendors" ON vendors FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_documents" ON documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_security_reviews" ON security_reviews FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_audit_logs" ON audit_logs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_policies" ON policies FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_breaches" ON breaches FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_vendor_review_states" ON vendor_review_states FOR ALL USING (true) WITH CHECK (true);

-- ============================================
-- Storage bucket for vendor documents
-- ============================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('vendor-documents', 'vendor-documents', false)
ON CONFLICT (id) DO NOTHING;


-- ============================================
-- PHASE 2: Compliance, Financial & Evidence
-- ============================================

-- ============================================
-- Table: compliance_reviews
-- ============================================
CREATE TABLE IF NOT EXISTS compliance_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    overall_score DECIMAL(5, 2),
    grade VARCHAR(2),
    gdpr_score DECIMAL(5, 2),
    hipaa_score DECIMAL(5, 2),
    pci_score DECIMAL(5, 2),
    dpa_score DECIMAL(5, 2),
    privacy_policy_score DECIMAL(5, 2),
    applicable_regulations JSONB DEFAULT '[]',
    findings JSONB DEFAULT '[]',
    gaps JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    report JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Table: financial_reviews
-- ============================================
CREATE TABLE IF NOT EXISTS financial_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    overall_score DECIMAL(5, 2),
    grade VARCHAR(2),
    insurance_score DECIMAL(5, 2),
    credit_rating_score DECIMAL(5, 2),
    financial_stability_score DECIMAL(5, 2),
    bcp_score DECIMAL(5, 2),
    insurance_details JSONB DEFAULT '{}',
    credit_details JSONB DEFAULT '{}',
    financial_analysis JSONB DEFAULT '{}',
    findings JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    report JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Table: evidence_requests
-- ============================================
CREATE TABLE IF NOT EXISTS evidence_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    document_type VARCHAR(100) NOT NULL,
    criticality VARCHAR(50) DEFAULT 'required',
    reason TEXT,
    requested_by VARCHAR(100) DEFAULT 'evidence_coordinator',
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP WITH TIME ZONE,
    email_recipient VARCHAR(255),
    deadline DATE,
    status VARCHAR(50) DEFAULT 'pending',
    response_received_at TIMESTAMP WITH TIME ZONE,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Table: evidence_tracking
-- ============================================
CREATE TABLE IF NOT EXISTS evidence_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    evidence_request_id UUID REFERENCES evidence_requests(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    actor VARCHAR(100) DEFAULT 'system',
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Phase 2 Indexes
-- ============================================
CREATE INDEX IF NOT EXISTS idx_compliance_reviews_vendor_id ON compliance_reviews(vendor_id);
CREATE INDEX IF NOT EXISTS idx_financial_reviews_vendor_id ON financial_reviews(vendor_id);
CREATE INDEX IF NOT EXISTS idx_evidence_requests_vendor_id ON evidence_requests(vendor_id);
CREATE INDEX IF NOT EXISTS idx_evidence_requests_status ON evidence_requests(status);
CREATE INDEX IF NOT EXISTS idx_evidence_tracking_vendor_id ON evidence_tracking(vendor_id);
CREATE INDEX IF NOT EXISTS idx_evidence_tracking_request_id ON evidence_tracking(evidence_request_id);

-- ============================================
-- Phase 2 RLS
-- ============================================
ALTER TABLE compliance_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_compliance_reviews" ON compliance_reviews FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_financial_reviews" ON financial_reviews FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_evidence_requests" ON evidence_requests FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_evidence_tracking" ON evidence_tracking FOR ALL USING (true) WITH CHECK (true);
