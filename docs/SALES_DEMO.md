# 12-minute Sales Demo

## 1. Show the mess (1 min)
Open `sample_data/`: quality Excel, process CSV, sensor CSV, part-lot CSV, maintenance Excel, manuals, camera sample and machine-audio samples use different formats.

## 2. Show automatic catalog (1 min)
Open `/data`. Explain canonical mapping and SHA-256 provenance.

## 3. Trigger a camera event (2 min)
Open `/vision` and run `cam-body-03` one-frame analysis. Show the annotated image, critical defect event and human-review queue. Explain that a real deployment can use USB/RTSP + a customer-trained YOLOX model, or an Anomalib sidecar for unknown defects.

## 4. Ask one concrete incident (3 min)
Use: `QV-017の品質NGの原因候補を調べて。停止と継続も比較して`.

Show that the system:
- traces passed equipment;
- compares NG rates;
- detects sensor deviations;
- checks part lot association;
- retrieves prior maintenance / troubleshooting evidence;
- **adds the camera event as another evidence source**;
- ranks what an engineer should check first.

## 5. Show forward-looking intelligence (2 min)
Open `/intelligence`:
- sensor health;
- process variants and bottleneck;
- drift monitoring;
- machine-sound anomaly;
- trend-to-abnormal-band forecast;
- maintenance scheduling.

Clarify that the forecast is not falsely marketed as RUL until failure-labelled data exists.

## 6. Show trust / enterprise fit (2 min)
Show data-quality gate, source references, case history, audit, API/RBAC hooks and deployment choices: laptop PoC vs PostgreSQL/Qdrant/SSO stack. External LLM is off by default.

## 7. Close with paid pilot (1 min)
Propose one plant / one defect family / 3-5 data sources / 1-2 camera points. Baseline investigation lead time, false-reject/escape rate and engineer search time, then compare after deployment.
