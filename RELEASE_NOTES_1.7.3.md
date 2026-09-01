# 1.7.3 Warm Teal hard fix

- Uses a new top-level folder and port 8173 so an older 8000 server cannot be mistaken for this build.
- Uses a new CSS asset name to bypass stale browser caches.
- Hard-fixes the reported dark surfaces on Adaptive Analysis, Onboarding, Approval Center, and Process/Equipment AI.
- Repairs the common UTF-8-as-CP932 mojibake at the data ingestion/display boundary.
- Keeps Japanese sample filenames in UTF-8 ZIP metadata.
