from __future__ import annotations

"""Automatic capability discovery for partially populated factory datasets.

The product is intentionally data-optional: missing datasets disable only the
modules that need them.  Nothing in this file interprets a missing role as an
application failure.
"""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR, ROOT, VISION_CONFIG
from .schema import TableProfile, choose_role_tables_multi, scan_tables

DOC_EXTS = {".pdf", ".docx", ".txt", ".md"}
AUDIO_EXTS = {".wav"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


@dataclass
class ModuleCapability:
    id: str
    name: str
    enabled: bool
    state: str
    route: str
    description: str
    requires_all: list[str] = field(default_factory=list)
    requires_any: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    enrichments: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _camera_counts(data_dir: Path) -> tuple[int, int]:
    if not VISION_CONFIG.exists():
        return 0, 0
    try:
        raw = json.loads(VISION_CONFIG.read_text(encoding="utf-8"))
        configured = len(raw) if isinstance(raw, list) else 0
        enabled = 0
        for x in raw if isinstance(raw, list) else []:
            if not isinstance(x, dict) or not bool(x.get("enabled", True)):
                continue
            # The shipped synthetic camera must not make Vision look enabled in a
            # customer deployment that points DATA_DIR somewhere else. Live or
            # non-demo camera configs remain valid regardless of DATA_DIR.
            detector_type = str((x.get("detector") or {}).get("type", "")).lower()
            if detector_type == "demo":
                src = Path(str(x.get("source", "")))
                src = src if src.is_absolute() else ROOT / src
                try:
                    src.resolve().relative_to(data_dir.resolve())
                except Exception:
                    continue
            enabled += 1
        return configured, enabled
    except Exception:
        return 0, 0


def _files(data_dir: Path, exts: set[str]) -> list[Path]:
    if not data_dir.exists():
        return []
    return [p for p in data_dir.rglob("*") if p.is_file() and p.suffix.lower() in exts]


def _role_sources(grouped: dict[str, list[TableProfile]]) -> dict[str, list[str]]:
    return {role: [p.label for p in profiles] for role, profiles in grouped.items() if profiles}


def _module(
    *,
    id: str,
    name: str,
    route: str,
    description: str,
    signals: dict[str, bool],
    requires_all: list[str] | None = None,
    requires_any: list[str] | None = None,
    optional: list[str] | None = None,
) -> ModuleCapability:
    req_all = list(requires_all or [])
    req_any = list(requires_any or [])
    opt = list(optional or [])
    missing_all = [x for x in req_all if not signals.get(x, False)]
    any_ok = True if not req_any else any(signals.get(x, False) for x in req_any)
    missing_any = [] if any_ok else list(req_any)
    enabled = not missing_all and any_ok
    enrich = [x for x in opt if signals.get(x, False)]
    missing = missing_all + missing_any
    return ModuleCapability(
        id=id,
        name=name,
        enabled=enabled,
        state="ready" if enabled else "waiting_data",
        route=route,
        description=description,
        requires_all=req_all,
        requires_any=req_any,
        optional=opt,
        missing=missing,
        enrichments=enrich,
    )


def detect_capabilities(
    data_dir: Path = DATA_DIR,
    *,
    profiles: list[TableProfile] | None = None,
    chunks: list[Any] | None = None,
) -> dict[str, Any]:
    profiles = profiles if profiles is not None else scan_tables(data_dir)[0]
    grouped = choose_role_tables_multi(profiles)
    roles = _role_sources(grouped)

    docs = _files(data_dir, DOC_EXTS)
    audio = _files(data_dir, AUDIO_EXTS)
    images = _files(data_dir, IMAGE_EXTS)
    camera_configured, camera_enabled = _camera_counts(data_dir)

    signals = {
        "quality": bool(grouped.get("quality")),
        "process": bool(grouped.get("process")),
        "equipment_logs": bool(grouped.get("equipment_logs")),
        "maintenance": bool(grouped.get("maintenance")),
        "parts": bool(grouped.get("parts")),
        "documents": bool(docs) or bool(chunks),
        "vision": camera_enabled > 0,
        "acoustic": len(audio) >= 2,
    }

    specs = [
        _module(id="root_cause", name="品質×工程 原因探索", route="/investigate", description="品質NGと工程トレースを結び、設備・ロット・保全・画像検査を根拠として原因候補を順位付けします。", signals=signals, requires_all=["quality", "process"], optional=["equipment_logs", "maintenance", "parts", "documents", "vision"]),
        _module(id="quality_trends", name="品質傾向分析", route="/investigate", description="品質データだけでもNG傾向、不具合内訳、検査項目別の偏りを分析します。", signals=signals, requires_all=["quality"], optional=["parts", "documents"]),
        _module(id="quality_lot", name="品質×部品ロット", route="/investigate", description="品質と部品ロットがあれば、工程履歴なしでもロット別NG偏りを比較します。", signals=signals, requires_all=["quality", "parts"]),
        _module(id="process_intelligence", name="工程・ボトルネック分析", route="/intelligence", description="工程履歴だけで工程パターン、逸脱、サイクル時間、ボトルネックを可視化します。", signals=signals, requires_all=["process"]),
        _module(id="sensor_monitoring", name="設備異常監視", route="/intelligence", description="設備ログだけで電流・温度・振動等のロバスト異常度を算出します。", signals=signals, requires_all=["equipment_logs"], optional=["maintenance"]),
        _module(id="predictive_watch", name="閾値到達予測", route="/intelligence", description="設備時系列の直近トレンドから異常帯への到達を予測します。残存寿命（RUL）予測ではありません。", signals=signals, requires_all=["equipment_logs"]),
        _module(id="drift_monitoring", name="設備データドリフト", route="/intelligence", description="基準期間と直近期間の分布変化をPSI等で監視します。", signals=signals, requires_all=["equipment_logs"]),
        _module(id="maintenance_intelligence", name="保全履歴分析", route="/investigate", description="保全履歴だけでも設備別の再発傾向・頻出不具合・直近対応を整理します。", signals=signals, requires_all=["maintenance"], optional=["equipment_logs"]),
        _module(id="maintenance_optimizer", name="保全優先順位最適化", route="/intelligence", description="設備リスクが得られる場合に点検順と担当割当を提案します。", signals=signals, requires_all=["equipment_logs"]),
        _module(id="part_traceability", name="部品ロットトレーサビリティ", route="/investigate", description="部品ロットだけでも製品IDとロットの追跡・構成確認ができます。", signals=signals, requires_all=["parts"]),
        _module(id="rag_assistant", name="現場文書検索アシスタント", route="/investigate", description="PDF/Word/Markdown/TXTだけでも過去事例・標準書・手順書を検索できます。", signals=signals, requires_all=["documents"]),
        _module(id="vision_inspection", name="画像検査", route="/vision", description="カメラだけでもYOLOX/Anomalib/QR/追跡/ゾーンルールを単独運用できます。", signals=signals, requires_all=["vision"], optional=["quality", "process", "equipment_logs"]),
        _module(id="acoustic_monitoring", name="設備音異常", route="/intelligence", description="正常音と比較対象音があれば、音響特徴量による設備状態監視を単独運用できます。", signals=signals, requires_all=["acoustic"], optional=["equipment_logs"]),
    ]

    modules = {m.id: m.as_dict() for m in specs}
    active = [m.id for m in specs if m.enabled]
    waiting = [m.id for m in specs if not m.enabled]
    return {
        "signals": signals,
        "roles": roles,
        "files": {
            "documents": [str(p.relative_to(data_dir)) for p in docs],
            "audio": [str(p.relative_to(data_dir)) for p in audio],
            "images": [str(p.relative_to(data_dir)) for p in images],
        },
        "vision": {"configured_cameras": camera_configured, "enabled_cameras": camera_enabled},
        "modules": modules,
        "active_modules": active,
        "waiting_modules": waiting,
        "active_count": len(active),
        "total_count": len(specs),
        "ready": bool(active),
    }


def preferred_prompt(capabilities: dict[str, Any]) -> str:
    mods = capabilities.get("modules", {})
    if mods.get("root_cause", {}).get("enabled"):
        return "QV-017の品質NGの原因候補を調べて。停止と継続も比較して"
    if mods.get("sensor_monitoring", {}).get("enabled"):
        return "設備ログから異常度が高い設備と信号をランキングして"
    if mods.get("quality_trends", {}).get("enabled"):
        return "品質データからNG傾向と優先して確認すべき不具合を分析して"
    if mods.get("process_intelligence", {}).get("enabled"):
        return "工程履歴からボトルネックと工程逸脱を分析して"
    if mods.get("maintenance_intelligence", {}).get("enabled"):
        return "保全履歴から再発傾向と優先点検設備を整理して"
    if mods.get("rag_assistant", {}).get("enabled"):
        return "登録文書から関連する過去事例と手順を探して"
    if mods.get("part_traceability", {}).get("enabled"):
        return "部品ロットデータの構成と追跡可能な項目を整理して"
    return "利用可能なデータからできる分析を実行して"
