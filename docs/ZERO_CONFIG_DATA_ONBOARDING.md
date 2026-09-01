# Zero-Config Data Onboarding

Version: 1.5.1-deepseek-flash-full-embedded-rc1

## Goal

The user should not have to reshape a factory Excel workbook into a product-specific template before using Factory Decision Copilot.

The onboarding pipeline is:

1. discover files;
2. profile every table and column;
3. infer column semantics;
4. infer one or more table roles;
5. propose relationships / JOINs across files;
6. ask for human review only where confidence is insufficient;
7. learn approved mappings locally;
8. recompute the Capability Registry;
9. automatically run the best available analysis.

## Local semantic profiler

For each column the default engine computes:

- original header;
- pandas dtype;
- semantic type: numeric / datetime / categorical / string;
- first sample values;
- null ratio;
- unique count and unique ratio;
- numeric parse ratio;
- datetime parse ratio;
- ID-like string ratio;
- leading-zero ratio;
- OK/NG-like token ratio;
- numeric min/max/median/mean where applicable.

This is combined with Japanese/English manufacturing aliases and cross-column relationships.

Example unknown headers:

| Raw | Inferred canonical |
| --- | --- |
| 号口 | vehicle_id |
| 実績年月日 | timestamp |
| 工程コード | process |
| 号機 | equipment_id |
| 結果区分 | result |
| 実測 | value |
| 上規格 | upper_limit |
| 下規格 | lower_limit |

## Confidence policy

- >= 95%: AUTO candidate
- 80-94%: REVIEW recommended
- 62-79%: REVIEW / low confidence
- < 62%: unresolved; not mapped automatically

A low-confidence field never needs to block ingestion of the rest of the table.

## Human-in-the-loop schema memory

`/onboarding` lets an engineer correct inferred columns and table roles. If “learn” is checked, the approved alias is persisted to:

`runtime/schema_memory.json`

The next file containing the same company-specific header receives that approved mapping first.

This memory is local to the deployment. It is not sent to an external service.

## One table can serve multiple roles

A factory export often combines quality, process and machine information in one sheet. A table is therefore allowed to be compatible with several semantic roles simultaneously.

Example:

`号口 + 号機 + 工程コード + 結果区分 + 実績年月日 + 電流値`

can enable:

- quality trends;
- process traceability;
- equipment sensor analysis.

The primary inferred role is still shown for readability, but capability activation uses all compatible roles.

## JOIN discovery

The engine proposes relationships using canonical fields and sample-value overlap.

Supported patterns include:

- product/vehicle ID equi-join;
- equipment ID equi-join;
- part-lot / part-number equi-join;
- process-code relationship;
- timestamp time-window relationship;
- equipment ID + timestamp as-of relationship for sensor alignment.

JOIN suggestions include confidence, reasoning and an approval state.

## DeepSeek V4 Flash semantic enhancement

When `DEEPSEEK_API_KEY` is configured, low-confidence schema inference and cross-file JOIN reasoning are augmented by `deepseek-v4-flash`. The local profiler remains the deterministic base and can operate fully offline when no key is configured.

This private build already includes the API key in `.env.local`.

FULL mode is enabled: sample values, retrieved document text and structured factory evidence are available to DeepSeek V4 Flash.

## File upload UX

Open:

`http://127.0.0.1:8000/onboarding`

Drag and drop one or more files. The server stores uploads under the configured `DATA_DIR/uploads`, rescans schemas, refreshes capabilities and runs the preferred currently available analysis locally.

## Google Drive

Two optional patterns are included:

### Drive for desktop / enterprise synced folder

```bash
python scripts/import_google_drive_folder.py --synced-folder "G:/My Drive/FactoryData"
```

### Drive API by folder ID

Install optional dependencies:

```bash
pip install -r requirements-google-drive.txt
```

Share the folder with a read-only service account, then:

```bash
python scripts/import_google_drive_folder.py \
  --folder-id YOUR_FOLDER_ID \
  --credentials /secure/path/service-account.json
```

The API connector is read-only. Core product operation does not require Google Drive or internet access.
