from __future__ import annotations

import argparse
from pathlib import Path

from app.config import DATA_DIR
from integrations.google_drive_ingest import import_drive_folder, import_synced_folder


def main():
    ap = argparse.ArgumentParser(description="Import a Google Drive folder into Factory Decision Copilot")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--synced-folder", help="Local Google Drive for desktop folder")
    group.add_argument("--folder-id", help="Google Drive folder ID for service-account API import")
    ap.add_argument("--credentials", help="Service-account JSON (required with --folder-id)")
    ap.add_argument("--destination", default=str(DATA_DIR / "google_drive"))
    args = ap.parse_args()
    dest = Path(args.destination)
    if args.synced_folder:
        files = import_synced_folder(Path(args.synced_folder), dest)
    else:
        if not args.credentials:
            ap.error("--credentials is required with --folder-id")
        files = import_drive_folder(args.folder_id, Path(args.credentials), dest)
    print(f"Imported {len(files)} files into {dest}")
    for f in files[:50]:
        print(" -", f)


if __name__ == "__main__":
    main()
