# Commercialization Checklist

This repository is an enterprise-grade prototype / release candidate, not a claim of production certification.

## Product validation
- [ ] Confirm one paid pilot use case and baseline investigation time.
- [ ] Define measurable target: e.g. investigation lead-time reduction, first-pass yield, repeat-defect reduction.
- [ ] Validate hypotheses against confirmed root-cause records.
- [ ] Add customer-specific adapters for QMS/MES/SCADA/PLM data.
- [ ] Confirm false-positive/false-negative tolerances with process owners.

## Security
- [ ] Threat model review.
- [ ] Corporate SSO integration and least-privilege roles.
- [ ] TLS termination and certificate rotation.
- [ ] Secrets vault integration.
- [ ] Vulnerability scanning / SBOM / dependency pinning.
- [ ] Penetration test.
- [ ] Data retention and deletion policy.
- [ ] Export audit logs to SIEM.

## Reliability
- [ ] PostgreSQL backup/restore drill.
- [ ] Qdrant backup/reindex procedure.
- [ ] Load test using customer data volumes.
- [ ] HA requirements and RTO/RPO agreement.
- [ ] Offline/failure behavior documented.

## AI governance
- [ ] Model registry and approval workflow.
- [ ] Dataset/model lineage.
- [ ] Drift monitoring.
- [ ] Human confirmation for root-cause and operational actions.
- [ ] No autonomous PLC control without a separately validated safety architecture.

## Legal/commercial
- [ ] OSS license and NOTICE audit for exact shipped components.
- [ ] Customer data processing terms.
- [ ] Warranty/SLA/support boundaries.
- [ ] IP ownership for customer-specific adapters.
- [ ] Product liability review for any operational recommendation features.
