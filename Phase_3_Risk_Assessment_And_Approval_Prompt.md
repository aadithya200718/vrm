# Phase 3: ML Risk Assessment & Multi-Step Approval Workflow

## Objective
Implement the ML-powered risk assessment layer (Bayesian scoring, Reinforcement Learning, Continual Learning, Federated Learning) and the human-in-the-loop approval workflow (3-step for SaaS, 4-step for Healthcare with Compliance Officer final review).

## Context
Building on Phase 2's verification results, this phase adds intelligent risk scoring using multiple ML models and routes vendors through role-based approval workflows. Healthcare vendors require stricter assessment (HIPAA checks weighted 2x) and an additional Compliance Officer approval step. The system must handle model disagreements, provide explainable risk scores, and support continuous learning from approval outcomes.

## Bayesian Risk Scoring Agent

### Core Bayesian Inference Engine

**Celery Task:** `calculate_bayesian_risk_task` (triggered after all verifications complete)

**SaaS Bayesian Scoring:**
- Input: All confidence scores from `verification_results` table
- Prior: Historical SaaS vendor approval rate from `risk_model_feedback` (typically ~75%)
- Likelihood Updates:
  - GST verification confidence → update posterior
  - PAN verification confidence → update posterior
  - Bank validation confidence → update posterior
  - Sanctions check confidence → update posterior
  - MCA verification confidence → update posterior
  - SOC 2 parser confidence → update posterior
- Tool: PyMC or scikit-learn BayesianRidge
- Workflow:
  1. Fetch all verification results for vendor
  2. Initialize prior P(legitimate) = 0.75
  3. For each verification result:
     - Apply Bayes theorem: P(legitimate|evidence) = P(evidence|legitimate) × P(legitimate) / P(evidence)
     - Update posterior probability
  4. Calculate confidence interval (±X%)
  5. Determine risk tier:
     - P(legitimate) > 0.85 → Tier 3 (Low Risk)
     - 0.65 < P(legitimate) ≤ 0.85 → Tier 2 (Medium Risk)
     - P(legitimate) ≤ 0.65 → Tier 1 (High Risk)
  6. Generate evidence explanation: "Score increased 0.15 by GST verification, decreased 0.08 by sanctions check"
  7. Apply hard overrides:
     - Sanctions FLAGGED → AUTO_REJECT (override all scores)
  8. Store in `bayesian_scores` table
- Output: `{ probability_legitimate, probability_fraud, confidence_interval, risk_tier, evidence_explanation, hard_override }`

**Healthcare Bayesian Scoring:**
- Input: Confidence scores from BOTH `verification_results` AND `hipaa_verifications` tables
- Prior: Historical Healthcare vendor approval rate (typically ~65%, lower due to stricter requirements)
- Likelihood Updates:
  - Standard checks (GST, PAN, bank, MCA): weight = 1.0
  - HIPAA checks (OIG, BAA, attestation, ePHI flow, subprocessors): weight = 2.0 (CRITICAL)
- Workflow: Same as SaaS but with weighted updates
- Hard Overrides (Healthcare-specific):
  - OIG excluded → AUTO_REJECT (cannot be overridden)
  - BAA missing breach notification clause → Tier 1 BLOCK
  - ePHI leaving jurisdiction → Tier 1 BLOCK
- Output: Same as SaaS plus `{ hipaa_overrides: [], hipaa_risk_factors: [] }`

### Risk Tier Determination

**Tier 3 (Low Risk):**
- P(legitimate) > 0.85
- All verifications passed with high confidence
- No HIPAA violations (Healthcare)
- Approval: Legal + Finance + IT (SaaS) or + Compliance Officer (Healthcare)

**Tier 2 (Medium Risk):**
- 0.65 < P(legitimate) ≤ 0.85
- Some verifications with medium confidence
- Minor HIPAA concerns (Healthcare)
- Approval: Same as Tier 3 but with conditional approval possible

**Tier 1 (High Risk):**
- P(legitimate) ≤ 0.65
- Multiple verifications failed or low confidence
- Major HIPAA violations (Healthcare)
- Approval: Requires unanimous approval + additional conditions

**AUTO_REJECT:**
- Sanctions flagged (SaaS)
- OIG excluded (Healthcare)
- BAA critical clause missing (Healthcare)
- ePHI jurisdiction violation (Healthcare)

## Reinforcement Learning Risk Model

### RL Environment Setup

**State Vector (SaaS - 8 dimensions):**
1. GST verification confidence (0.0-1.0)
2. PAN verification confidence (0.0-1.0)
3. Bank validation confidence (0.0-1.0)
4. Sanctions check confidence (0.0-1.0)
5. MCA verification confidence (0.0-1.0)
6. SOC 2 type (0=none, 0.5=Type I, 1.0=Type II)
7. SOC 2 days to expiry (normalized 0.0-1.0)
8. Company age in years (normalized 0.0-1.0)

**State Vector (Healthcare - 12 dimensions):**
- All 8 SaaS dimensions PLUS:
9. OIG check result (0.0=excluded, 1.0=clear)
10. BAA completeness (0.0-1.0, based on clauses present/6)
11. HIPAA attestation validity (0.0-1.0)
12. ePHI flow safety score (0.0-1.0)
13. Subprocessor coverage (0.0-1.0)

**Actions:**
- Action 0: Recommend Tier 3 (Low Risk)
- Action 1: Recommend Tier 2 (Medium Risk)
- Action 2: Recommend Tier 1 (High Risk)
- Action 3: Recommend Auto-Reject

**Reward Function (SaaS):**
- Correct Tier 3 approval (vendor performs well) → +1.0
- Correct Tier 1 block (vendor would have failed) → +2.0
- False approval (vendor later fails/fraud) → -5.0
- False block (vendor was legitimate) → -1.0

**Reward Function (Healthcare - Higher Penalties):**
- Correct Tier 3 approval → +1.0
- Correct Tier 1 block → +2.0
- False approval (vendor later HIPAA non-compliant) → -8.0
- False approval (vendor causes data breach) → -10.0
- False block → -1.0

### RL Model Training

**Bootstrap Training:**
- Celery task: `train_rl_model_task` (rl_training_queue)
- Worker-2 picks task
- Generate 500 synthetic vendor profiles (250 SaaS, 250 Healthcare)
- Train PPO model (Stable Baselines3) for 10,000 episodes
- Save model weights to `/models/rl_model_v1.pkl`
- Log version in `model_versions` table with accuracy metrics

**Live Retraining:**
- Celery task: `retrain_rl_model_task` (rl_training_queue)
- Triggered after each vendor outcome confirmed (approved vendor completes onboarding or fails)
- Workflow:
  1. Fetch vendor's state vector and actual outcome
  2. Calculate reward based on prediction vs outcome
  3. Store episode in `rl_training_episodes` table
  4. Retrain model incrementally (5 epochs)
  5. Evaluate on validation set
  6. If accuracy improves → save new version, update `model_versions`
  7. If accuracy degrades → rollback to previous version

### RL + Bayesian Integration

**Celery Task:** `generate_risk_assessment_task` (triggered after Bayesian scoring)
- Input: vendor_id, bayesian_score, state_vector
- Workflow:
  1. Load latest RL model from `model_versions`
  2. Predict action (Tier 3/2/1/Reject) from state vector
  3. Compare with Bayesian risk tier
  4. If models agree → high confidence (green flag)
  5. If models disagree → low confidence (yellow flag, mandatory human review)
  6. Generate executive summary with both scores
  7. Store in `risk_assessment` table
- Output: `{ bayesian_tier, rl_tier, models_agree, confidence_indicator, executive_summary }`

## Continual Learning Module

### Online Learning with River

**Celery Task:** `update_continual_model_task` (continual_learning_queue)
- Worker-1 picks task after each vendor outcome
- Tool: River LogisticRegression (online ML library)
- Workflow:
  1. Fetch vendor's verification results and outcome
  2. Convert to feature vector (same as RL state vector)
  3. Update River model weights with new sample
  4. Apply EWC (Elastic Weight Consolidation) to prevent catastrophic forgetting
  5. Store updated model weights
  6. Log performance metrics

**Healthcare Pattern Learning:**
- Detects emerging HIPAA violation patterns:
  - New subprocessor risks (e.g., new cloud region found non-compliant)
  - Evolving BAA clause fraud patterns
  - New ePHI flow vulnerabilities
- If new high-risk pattern detected (confidence > 0.9):
  - Publish alert to `notification_queue` for Compliance Officer
  - Update pattern database for future checks

**Model Monitoring:**
- Celery beat task: `evaluate_continual_model` (runs every 30 days)
- Workflow:
  1. Evaluate model accuracy on recent outcomes (last 30 days)
  2. If accuracy < 75% → publish alert to admin
  3. If accuracy < 60% → trigger full model retraining
  4. Log evaluation results in `model_versions`

## Federated Learning Module

### FL Client (Per Organization Instance)

**Celery Task:** `federated_training_task` (federated_queue)
- Celery beat: triggers every 30 days
- Worker-1 picks task
- Workflow:
  1. Fetch all vendor outcomes from last 30 days
  2. Train local RL model + LogisticRegression on local data (5 epochs)
  3. Calculate weight deltas (new_weights - old_weights)
  4. Apply Differential Privacy: add Gaussian noise to deltas
  5. Encrypt deltas (homomorphic encryption)
  6. Send encrypted deltas to FL Server
  7. Receive updated global model from FL Server
  8. Update local model with global weights
  9. Log FL round in `model_versions`

### FL Server (Separate Docker Service)

**Service:** `fl-server` (separate FastAPI microservice in docker-compose)
- Tool: Flower (flwr) framework
- Workflow:
  1. Receive encrypted weight deltas from all FL clients
  2. Aggregate encrypted gradients (homomorphic encryption allows aggregation without decryption)
  3. Decrypt aggregated result
  4. Apply FedAvg: weighted average of all deltas
  5. Broadcast updated global model to all clients
  6. Log FL round metrics

**HIPAA Privacy Guarantees:**
- No ePHI ever transmitted (only model weight numbers)
- Differential Privacy prevents vendor identity reconstruction from gradients
- Homomorphic Encryption means FL Server cannot read individual client gradients
- Cross-org learning: one hospital's fraud pattern helps all hospitals without sharing data

## Multi-Step Approval Workflow

### LangGraph Approval Routing

**Supervisor Node:** `approval_router`
- Input: vendor_id, risk_tier, workflow_type (saas|healthcare)
- Workflow:
  1. Create approval record in `approvals` table
  2. Determine required approvers based on risk tier and workflow type
  3. Set approval deadline (7 days for Tier 3, 14 days for Tier 1/2)
  4. Use LangGraph `interrupt()` to pause workflow
  5. Publish notification to first approver
  6. Wait for approval decision
  7. Resume workflow on decision received
  8. Route to next approver or complete

### SaaS Approval Workflow (3-Step)

**Step 1: Legal Team Approval**
- Endpoint: `POST /api/v1/approvals/{vendor_id}/legal`
- Auth: JWT (legal role)
- Request body: `{ decision: "approve"|"reject"|"request_changes", comments, conditions: [] }`
- Dashboard shows:
  - NDA/MSA document links
  - Bayesian P(legitimate) with confidence interval
  - RL model prediction
  - Model confidence indicator (green/yellow)
  - Verification results summary
- Workflow:
  1. Validate JWT and legal role
  2. Store decision in `approvals` table
  3. If reject → update vendor status to REJECTED, publish rejection notification
  4. If approve → resume LangGraph workflow to Step 2
  5. If request_changes → publish change request to vendor
- Output: `{ status, decision_id, next_step: "finance" }`

**Step 2: Finance Team Approval**
- Endpoint: `POST /api/v1/approvals/{vendor_id}/finance`
- Auth: JWT (finance role)
- Dashboard shows:
  - Bank validation results
  - Contract value
  - Payment terms
  - Bayesian + RL scores
- Workflow: Same as Step 1
- Output: `{ status, decision_id, next_step: "it" }`

**Step 3: IT Team Approval**
- Endpoint: `POST /api/v1/approvals/{vendor_id}/it`
- Auth: JWT (it role)
- Dashboard shows:
  - SOC 2 findings
  - ISO 27001 status
  - Pen test results
  - Bayesian + RL scores
  - Permission level configuration (read-only, read-write, admin)
- Workflow:
  1. Same as Step 1
  2. IT sets permission level in approval decision
  3. If all 3 approved → update status to FULLY_APPROVED
  4. Publish `setup_erp_task` to `approval_queue`
- Output: `{ status, decision_id, approval_complete: true, final_outcome: "approved" }`

### Healthcare Approval Workflow (4-Step)

**Steps 1-3:** Same as SaaS (Legal, Finance, IT)

**Step 4: Compliance Officer Approval (Healthcare-Only)**
- Endpoint: `POST /api/v1/healthcare/approvals/{vendor_id}/compliance`
- Auth: JWT (compliance_officer role)
- Dashboard shows ALL findings in unified view:
  - OIG exclusion check result
  - BAA clause analysis (6 clauses with status)
  - HIPAA attestation validation
  - ePHI data flow analysis with risk map
  - Subprocessor coverage report
  - Bayesian P(legitimate) with confidence interval (HIPAA-weighted)
  - RL model prediction
  - Model confidence indicator (green/yellow)
  - All standard verification results
- Workflow:
  1. Validate JWT and compliance_officer role
  2. Store decision in `approvals` table
  3. If reject → update status to REJECTED, publish rejection notification
  4. If approve → update status to FULLY_APPROVED
  5. Publish `setup_audit_trail_task` to `audit_log_queue` (Healthcare-specific)
  6. Publish `setup_erp_task` to `approval_queue`
- Output: `{ status, decision_id, approval_complete: true, final_outcome: "approved", hipaa_compliant: true }`

### Approval Dashboard Frontend

**Approver Dashboard (`/audit` or `/audit/{vendorId}`):**
- Existing component: `AuditPage.tsx`
- Enhancements needed:
  1. Fetch approval packet: `GET /api/v1/vendors/{id}/approval-packet`
  2. Display risk assessment:
     - Bayesian probability gauge (0-100%)
     - RL model recommendation badge
     - Confidence indicator (green=agree, yellow=disagree)
  3. Show verification results with confidence scores
  4. For Healthcare vendors:
     - Display HIPAA checks section separately
     - Show BAA clause checklist (6 clauses with ✓/✗)
     - Display ePHI flow risk map
     - Show OIG check result prominently
  5. Approval decision form:
     - Radio buttons: Approve / Reject / Request Changes
     - Comments textarea
     - Conditions checklist (for conditional approval)
     - Submit button
  6. Show approval history (previous approvers' decisions)
  7. Display deadline countdown

**Compliance Officer Dashboard (`/dashboard/compliance` - Healthcare):**
- New component needed
- Features:
  - All vendors in HIPAA pipeline
  - BAA expiry calendar view
  - Upcoming annual reassessments
  - ePHI access log viewer with CSV export
  - RAG query box for compliance searches
  - FL model accuracy across federated rounds
  - HIPAA agent success/failure rates

### Approval Workflow API Endpoints

**Get Approval Packet:**
- Endpoint: `GET /api/v1/vendors/{id}/approval-packet`
- Auth: JWT (approver roles)
- Returns: Complete approval package with all verification results, risk scores, documents, recommendations

**Get Approval Workflow:**
- Endpoint: `GET /api/v1/vendors/{id}/approval-workflow`
- Returns: Workflow configuration (3-step or 4-step), required approvers, current step, deadline

**Get Approval Decisions:**
- Endpoint: `GET /api/v1/vendors/{id}/approvals`
- Returns: History of all approval decisions with timestamps, approver names, comments

**Get Approval Status:**
- Endpoint: `GET /api/v1/vendors/{id}/approval-status`
- Returns: Current approval status, completion percentage, pending approvers, overdue flag

### Model Feedback Loop

**Celery Task:** `collect_approval_feedback_task`
- Triggered when vendor completes onboarding or fails post-approval
- Workflow:
  1. Fetch vendor's predicted risk tier (Bayesian + RL)
  2. Fetch actual outcome (success/failure/fraud/breach)
  3. Calculate reward for RL model
  4. Store in `risk_model_feedback` table
  5. Publish `retrain_rl_model_task` to `rl_training_queue`
  6. Publish `update_continual_model_task` to `continual_learning_queue`

## Implementation Checklist

### Bayesian Risk Scoring
- [ ] Implement SaaS Bayesian scoring with PyMC/BayesianRidge
- [ ] Implement Healthcare Bayesian scoring with 2x HIPAA weight
- [ ] Add hard override logic (sanctions, OIG, BAA critical clauses)
- [ ] Generate evidence explanations for score changes
- [ ] Store results in `bayesian_scores` and `hipaa_bayesian_scores` tables
- [ ] Create risk tier determination logic (Tier 3/2/1/Auto-Reject)

### Reinforcement Learning
- [ ] Define state vectors (8D for SaaS, 12D for Healthcare)
- [ ] Implement reward functions (higher penalties for Healthcare)
- [ ] Generate 500 synthetic vendor profiles for bootstrap training
- [ ] Train PPO model with Stable Baselines3
- [ ] Implement live retraining after each vendor outcome
- [ ] Store RL episodes in `rl_training_episodes` table
- [ ] Implement model versioning in `model_versions` table
- [ ] Create RL + Bayesian integration logic (agreement detection)

### Continual Learning
- [ ] Implement River LogisticRegression online model
- [ ] Add EWC to prevent catastrophic forgetting
- [ ] Implement Healthcare pattern learning (new HIPAA violations)
- [ ] Create alert system for new high-risk patterns
- [ ] Implement 30-day model evaluation (Celery beat)
- [ ] Add accuracy monitoring with alert thresholds

### Federated Learning
- [ ] Implement FL client (Celery task on federated_queue)
- [ ] Add Differential Privacy (Gaussian noise to gradients)
- [ ] Implement homomorphic encryption for weight deltas
- [ ] Create FL Server microservice (Flower framework)
- [ ] Implement FedAvg aggregation
- [ ] Add FL Server to docker-compose
- [ ] Test cross-org learning without data sharing
- [ ] Verify HIPAA privacy guarantees (no ePHI transmitted)

### SaaS Approval Workflow
- [ ] Implement Legal approval endpoint
- [ ] Implement Finance approval endpoint
- [ ] Implement IT approval endpoint with permission configuration
- [ ] Create LangGraph approval router with interrupt()
- [ ] Implement approval notification tasks
- [ ] Add approval deadline tracking (7 days Tier 3, 14 days Tier 1/2)
- [ ] Implement rejection notification task

### Healthcare Approval Workflow
- [ ] Implement all SaaS approval steps for Healthcare
- [ ] Implement Compliance Officer approval endpoint (4th step)
- [ ] Create unified HIPAA findings dashboard for Compliance Officer
- [ ] Implement audit trail setup task (triggered on approval)
- [ ] Add BAA expiry tracking
- [ ] Implement annual HIPAA reassessment scheduler

### Approval Dashboard Frontend
- [ ] Update AuditPage to fetch approval packet
- [ ] Display Bayesian probability gauge
- [ ] Display RL model recommendation
- [ ] Show model confidence indicator (green/yellow)
- [ ] Add approval decision form (approve/reject/request changes)
- [ ] Show approval history timeline
- [ ] Display deadline countdown
- [ ] For Healthcare: add HIPAA checks section
- [ ] For Healthcare: show BAA clause checklist visualization
- [ ] For Healthcare: display ePHI flow risk map
- [ ] Create Compliance Officer dashboard (Healthcare)

### Model Feedback Loop
- [ ] Implement approval feedback collection task
- [ ] Calculate rewards based on actual outcomes
- [ ] Store feedback in `risk_model_feedback` table
- [ ] Trigger RL retraining on feedback
- [ ] Trigger continual learning update on feedback
- [ ] Monitor model accuracy over time

## Success Criteria
- Bayesian scoring calculates P(legitimate) with confidence interval
- HIPAA checks weighted 2x in Healthcare Bayesian scoring
- Hard overrides work (OIG exclusion → auto-reject)
- RL model predicts risk tier from state vector
- RL + Bayesian models show agreement/disagreement indicator
- Continual learning model updates after each vendor outcome
- Federated learning completes 30-day rounds without sharing ePHI
- SaaS vendors route through 3-step approval (Legal → Finance → IT)
- Healthcare vendors route through 4-step approval (+ Compliance Officer)
- LangGraph interrupt() pauses workflow until approval received
- Approver dashboard shows Bayesian + RL scores
- Compliance Officer sees unified HIPAA findings
- Model feedback loop retrains RL model after outcomes
- Approval decisions stored with timestamps and comments
- Deadline tracking alerts overdue approvals

## Next Phase Preview
Phase 4 will implement the final activation and monitoring components: ERP setup agent (vendor code generation, Zoho Books/SAP integration), audit trail setup for Healthcare vendors, scheduler agent (BAA renewal reminders, annual HIPAA reassessments, RL model retraining), RAG compliance query agent, vendor support chatbot (HIPAA-aware for Healthcare), and comprehensive testing (unit, integration, security, observability). This phase also covers deployment to docker-compose locally, Minikube (bonus), and cloud (Render + Vercel).
