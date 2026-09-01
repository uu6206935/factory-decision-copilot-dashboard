from prometheus_client import Counter, Histogram, Gauge

ANALYSIS_COUNT = Counter("factory_copilot_analysis_total", "Number of analysis requests", ["status"])
ANALYSIS_LATENCY = Histogram("factory_copilot_analysis_seconds", "Analysis latency seconds")
INGEST_COUNT = Counter("factory_copilot_ingest_total", "Number of ingestion scans", ["status"])
CATALOG_FILES = Gauge("factory_copilot_catalog_files", "Files currently indexed")
CATALOG_TABLES = Gauge("factory_copilot_catalog_tables", "Structured tables currently indexed")
CATALOG_CHUNKS = Gauge("factory_copilot_catalog_chunks", "Document chunks currently indexed")
