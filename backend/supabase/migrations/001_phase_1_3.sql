create extension if not exists pgcrypto;
create extension if not exists vector;

create type workflow_type as enum ('saas', 'healthcare');
create type approval_decision as enum ('approve', 'reject', 'request_changes');

create table if not exists vendor_requests (
  id uuid primary key default gen_random_uuid(),
  employee_email text not null,
  vendor_name text not null,
  service_type text not null,
  reason text not null,
  contract_value numeric not null,
  contact_email text not null,
  workflow_type workflow_type not null default 'saas',
  ephi_involved boolean not null default false,
  ephi_types jsonb not null default '[]'::jsonb,
  hipaa_required boolean not null default false,
  status text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists vendors (
  id uuid primary key default gen_random_uuid(),
  request_id uuid references vendor_requests(id),
  name text not null,
  service_type text not null,
  workflow_type workflow_type not null,
  status text not null,
  contract_value numeric not null,
  contact_email text not null,
  encrypted_pan bytea,
  encrypted_gst bytea,
  encrypted_bank_account bytea,
  domain text,
  vendor_type text,
  current_phase text,
  current_agent text,
  current_step text,
  progress_percentage numeric default 0,
  overall_risk_score numeric,
  risk_level text,
  approval_tier text,
  approval_status text,
  approval_id uuid,
  ephi_involved boolean not null default false,
  ephi_types jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists vendor_documents (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  file_name text not null,
  file_type text not null,
  document_type text,
  classification text,
  classification_confidence numeric,
  processing_status text not null default 'queued',
  extracted_text text,
  extracted_metadata jsonb not null default '{}'::jsonb,
  extracted_dates jsonb not null default '{}'::jsonb,
  storage_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists verification_results (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  kind text not null,
  workflow_type workflow_type not null,
  status text not null,
  result text not null,
  confidence_score numeric not null,
  details jsonb not null default '{}'::jsonb,
  agent_name text not null,
  queue_name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists approvals (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  workflow_type workflow_type not null,
  status text not null,
  approval_tier text not null,
  required_approvers jsonb not null default '[]'::jsonb,
  current_step_role text,
  completion_percentage numeric not null default 0,
  deadline timestamptz,
  final_decision text,
  permission_level text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists approval_decisions (
  id uuid primary key default gen_random_uuid(),
  approval_id uuid not null references approvals(id) on delete cascade,
  vendor_id uuid not null references vendors(id) on delete cascade,
  role text not null,
  approver_name text not null,
  approver_email text not null,
  decision approval_decision not null,
  comments text not null default '',
  conditions jsonb not null default '[]'::jsonb,
  permission_level text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists onboarding_tokens (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  request_id uuid not null references vendor_requests(id) on delete cascade,
  workflow_type workflow_type not null,
  token text not null unique,
  expires_at timestamptz not null,
  used boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists notifications_log (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid references vendors(id) on delete cascade,
  request_id uuid references vendor_requests(id) on delete cascade,
  recipient text not null,
  template text not null,
  subject text not null,
  status text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists hipaa_verifications (
  like verification_results including all
);

create table if not exists baa_records (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  status text not null,
  confidence_score numeric not null,
  clauses jsonb not null default '{}'::jsonb,
  clauses_missing jsonb not null default '[]'::jsonb,
  expiry_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ephi_access_log (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  actor_email text not null,
  actor_role text not null,
  action text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists scheduled_tasks (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  task_type text not null,
  due_at timestamptz not null,
  status text not null default 'scheduled',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists bayesian_scores (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  workflow_type workflow_type not null,
  probability_legitimate numeric not null,
  probability_fraud numeric not null,
  confidence_interval jsonb not null default '{}'::jsonb,
  risk_tier text not null,
  evidence_explanation jsonb not null default '[]'::jsonb,
  hard_override text,
  hipaa_overrides jsonb not null default '[]'::jsonb,
  hipaa_risk_factors jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists hipaa_bayesian_scores (
  like bayesian_scores including all
);

create table if not exists rl_training_episodes (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  workflow_type workflow_type not null,
  state_vector jsonb not null default '[]'::jsonb,
  action integer not null,
  reward numeric not null,
  actual_outcome text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists risk_model_feedback (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  workflow_type workflow_type not null,
  predicted_tier text not null,
  actual_outcome text not null,
  reward numeric not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists model_versions (
  id uuid primary key default gen_random_uuid(),
  model_name text not null,
  version text not null,
  workflow_type workflow_type,
  accuracy numeric,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists vendor_embeddings (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  document_id uuid not null references vendor_documents(id) on delete cascade,
  doc_type text not null,
  dimensions integer not null,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists workflow_events (
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references vendors(id) on delete cascade,
  event_type text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table vendor_requests enable row level security;
alter table vendors enable row level security;
alter table vendor_documents enable row level security;
alter table verification_results enable row level security;
alter table approvals enable row level security;
alter table approval_decisions enable row level security;
alter table onboarding_tokens enable row level security;
alter table notifications_log enable row level security;
alter table hipaa_verifications enable row level security;
alter table baa_records enable row level security;
alter table ephi_access_log enable row level security;
alter table scheduled_tasks enable row level security;
alter table bayesian_scores enable row level security;
alter table hipaa_bayesian_scores enable row level security;
alter table rl_training_episodes enable row level security;
alter table risk_model_feedback enable row level security;
alter table model_versions enable row level security;
alter table vendor_embeddings enable row level security;
alter table workflow_events enable row level security;

create policy "employee_vendor_requests_select"
on vendor_requests for select
using (auth.role() = 'authenticated');

create policy "vendor_self_token_select"
on onboarding_tokens for select
using (auth.role() = 'anon' or auth.role() = 'authenticated');

create policy "compliance_officer_hipaa_read"
on hipaa_verifications for select
using (coalesce(auth.jwt() ->> 'role', '') in ('compliance_officer', 'admin'));

create policy "compliance_officer_baa_read"
on baa_records for select
using (coalesce(auth.jwt() ->> 'role', '') in ('compliance_officer', 'legal', 'admin'));

create policy "compliance_officer_ephi_log_read"
on ephi_access_log for select
using (coalesce(auth.jwt() ->> 'role', '') in ('compliance_officer', 'admin'));

create policy "it_verification_read"
on verification_results for select
using (coalesce(auth.jwt() ->> 'role', '') in ('it', 'admin'));

create policy "legal_baa_read"
on baa_records for select
using (coalesce(auth.jwt() ->> 'role', '') in ('legal', 'admin'));

create or replace function block_ephi_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'ephi_access_log is append-only';
end;
$$;

drop trigger if exists ephi_access_log_block_update on ephi_access_log;
create trigger ephi_access_log_block_update
before update or delete on ephi_access_log
for each row execute function block_ephi_mutation();
