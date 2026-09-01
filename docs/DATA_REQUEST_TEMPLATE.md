# Data Request Template (safe dummy-data approach)

For each real data source, request only enough metadata to reproduce the structure with synthetic values:

- File / system name and purpose
- CSV / Excel / DB / API / PDF etc.
- Excel sheet names
- Column names
- Meaning of each column
- Data type: string / integer / decimal / date-time / category
- Unit and decimal precision
- Representative synthetic value (1-3 examples per field)
- Missing-value representation
- Primary / join keys (vehicle ID, serial, equipment ID, timestamp, part lot, process ID)
- Update frequency and approximate volume
- Time zone
- Whether history is corrected/overwritten or append-only

No real confidential value is required to build the first adapter.
