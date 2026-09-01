# Paid Pilot Plan

## Phase 0 — Data contract
Receive schema-only dummy data first. Build adapters without handling confidential values outside the approved environment.

## Phase 1 — Historical replay
Load a limited historical window. Pick incidents with known confirmed root causes and test whether the system ranks the confirmed cause/evidence highly enough to be useful.

## Phase 2 — Engineer shadow mode
Run alongside existing investigation workflow. The system makes suggestions but never controls equipment or closes a case automatically.

## Phase 3 — KPI review
Compare baseline vs pilot:
- median time to first useful hypothesis;
- manual system/file lookups per case;
- repeat issue discovery rate;
- percentage of answers with traceable evidence;
- engineer acceptance rate of top-N hypotheses.

## Phase 4 — Production decision
Only after security review, reliability requirements, data retention, SSO, backups, support ownership and operational governance are agreed.
