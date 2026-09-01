from __future__ import annotations

"""Optional Google Drive folder ingestion.

Two supported deployment patterns:
1) Google Drive for desktop / enterprise file sync: import a locally synced folder.
2) Google Drive API with a service account: import by Drive folder ID.

The core product does not require Google credentials or internet access.
"""

import io
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Iterable

DEFAULT_EXTS = {".csv", ".xlsx", ".xlsm", ".xls", ".json", ".pdf", ".docx", ".txt", ".md", ".wav", ".png", ".jpg", ".jpeg", ".bmp", ".webp"}

GOOGLE_EXPORTS = {
    "application/vnd.google-apps.spreadsheet": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.document": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
}


def _safe_name(name: str) -> str:
    p = Path(name)
    stem = re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠ー._ -]+", "_", p.stem).strip(" ._") or "drive_file"
    return stem[:120] + p.suffix.lower()


def import_synced_folder(source_dir: Path, destination_dir: Path, extensions: set[str] | None = None) -> list[Path]:
    extensions = extensions or DEFAULT_EXTS
    source_dir = source_dir.expanduser().resolve()
    destination_dir = destination_dir.resolve()
    imported: list[Path] = []
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(source_dir)
    for src in source_dir.rglob("*"):
        if not src.is_file() or src.suffix.lower() not in extensions:
            continue
        rel = src.relative_to(source_dir)
        dest = destination_dir / rel.parent / _safe_name(rel.name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        imported.append(dest)
    return imported


def import_drive_folder(folder_id: str, credentials_json: Path, destination_dir: Path, recursive: bool = True) -> list[Path]:
    """Download/export files from a Google Drive folder using a service account.

    Requires optional dependencies in requirements-google-drive.txt and the target
    folder to be shared with the service-account email.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError as exc:
        raise RuntimeError("Install requirements-google-drive.txt first") from exc

    creds = service_account.Credentials.from_service_account_file(
        str(credentials_json), scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    destination_dir.mkdir(parents=True, exist_ok=True)
    imported: list[Path] = []

    def list_children(fid: str):
        page = None
        while True:
            resp = service.files().list(
                q=f"'{fid}' in parents and trashed=false",
                fields="nextPageToken,files(id,name,mimeType,size,modifiedTime)",
                pageToken=page,
                pageSize=1000,
            ).execute()
            yield from resp.get("files", [])
            page = resp.get("nextPageToken")
            if not page:
                break

    def walk(fid: str, local: Path):
        for meta in list_children(fid):
            mime = meta.get("mimeType", "")
            name = _safe_name(meta.get("name", "drive_file"))
            if mime == "application/vnd.google-apps.folder":
                if recursive:
                    walk(meta["id"], local / name)
                continue
            export = GOOGLE_EXPORTS.get(mime)
            if export:
                export_mime, ext = export
                if not name.lower().endswith(ext):
                    name = str(Path(name).with_suffix(ext))
                request = service.files().export_media(fileId=meta["id"], mimeType=export_mime)
            else:
                suffix = Path(name).suffix.lower()
                if suffix not in DEFAULT_EXTS:
                    continue
                request = service.files().get_media(fileId=meta["id"])
            local.mkdir(parents=True, exist_ok=True)
            dest = local / name
            fh = io.FileIO(dest, "wb")
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.close()
            imported.append(dest)

    walk(folder_id, destination_dir)
    return imported
