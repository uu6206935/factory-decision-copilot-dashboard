# Release Notes — 1.4.0 Zero-Config Onboarding RC1

## Major feature: AI Schema Discovery

- Profile unknown Excel / CSV / JSON tables automatically.
- Infer manufacturing semantics from headers + values + data types + distributions.
- Return confidence, reasons, examples and alternative interpretations per column.
- Added common shop-floor labels including 号口, 号機, 実績年月日, 工程コード, 結果区分, 実測, 上規格 and 下規格.
- A single table can activate several semantic roles.

## Human review + learning

- New `/onboarding` drag-and-drop UX.
- Schema Review screen for correcting only uncertain/wrong mappings.
- Approved mappings can be learned locally for subsequent files.
- Table-role corrections are persisted.

## Relationship discovery

- Automatic JOIN candidates across files.
- Value-overlap scoring for vehicle/product, equipment, lot, part and process keys.
- Time-window and equipment+timestamp as-of suggestions.
- Human approval state for joins.

## Automatic product configuration

After file upload:

1. data is rescanned;
2. schema semantics are recomputed;
3. Capability Registry is recomputed;
4. newly available modules turn ON;
5. the best available analysis is run automatically.

## Optional LLM assistance

- Local semantic inference remains the default.
- Optional approved/internal OpenAI-compatible schema enhancement for low-confidence columns.
- Sample values are not sent unless separately enabled.

## Data source integration

- Browser multi-file upload.
- Google Drive for desktop / synced-folder importer.
- Optional read-only Google Drive API folder importer.

## Verification

- Existing Adaptive Data / Vision / Intelligence / Enterprise tests retained.
- Added zero-config schema inference, JOIN discovery, schema-learning and onboarding UI tests.
