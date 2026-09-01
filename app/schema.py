from __future__ import annotations

import json
import math
import re
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import RUNTIME_DIR
from .text_utils import display_filename, resolve_source_path

STRUCTURED_EXTS = {".csv", ".xlsx", ".xlsm", ".xls", ".json"}
SCHEMA_MEMORY = RUNTIME_DIR / "schema_memory.json"

# Canonical manufacturing semantics. The list deliberately includes common
# Japanese shop-floor labels that rarely appear in software-oriented datasets.
ALIASES: dict[str, list[str]] = {
    "vehicle_id": ["vehicle_id", "vehicle", "vin", "vin_no", "car_id", "unit_id", "serial_no", "product_id", "serial", "車両id", "車両番号", "車番", "管理番号", "製品id", "製品番号", "製造番号", "号口", "個体番号", "個体id", "ワークid"],
    "result": ["result", "judgement", "judgment", "status", "qc_result", "inspection_result", "判定", "合否", "結果", "結果区分", "判定区分", "okng", "ok_ng", "良否"],
    "defect_type": ["defect_type", "defect", "defect_name", "defect_code", "failure", "phenomenon", "不具合", "不良", "現象", "不具合内容", "不良内容", "不良項目", "異常項目"],
    "inspection_item": ["inspection_item", "item", "check_item", "検査項目", "測定項目", "項目", "検査コード", "測定コード"],
    "value": ["value", "measurement", "measured_value", "actual", "actual_value", "測定値", "実測値", "実測", "値", "計測値"],
    "lower_limit": ["lower_limit", "lsl", "min", "spec_min", "下限", "規格下限", "下規格", "下限規格", "下限値"],
    "upper_limit": ["upper_limit", "usl", "max", "spec_max", "上限", "規格上限", "上規格", "上限規格", "上限値"],
    "timestamp": ["timestamp", "datetime", "date_time", "inspection_time", "event_time", "recorded_at", "実績年月日", "実績日時", "実績日", "検査日時", "日時", "時刻", "年月日", "date", "time"],
    "process": ["process", "process_name", "process_code", "station", "station_name", "工程", "工程名", "工程コード", "ステーション", "工程区分"],
    "equipment_id": ["equipment_id", "equipment", "machine_id", "machine", "robot_id", "設備id", "設備番号", "設備", "機械番号", "ロボット番号", "号機", "機番", "設備コード"],
    "start_time": ["start_time", "process_start", "開始時刻", "開始日時", "工程開始", "着工日時"],
    "end_time": ["end_time", "process_end", "終了時刻", "終了日時", "工程終了", "完了日時"],
    "part_lot": ["part_lot", "lot", "lot_no", "lot_number", "部品ロット", "ロット", "ロット番号", "材料ロット", "lotno"],
    "part_no": ["part_no", "part_number", "品番", "部品番号", "部品コード", "材料コード"],
    "operator": ["operator", "worker", "作業者", "担当者", "作業者id", "社員番号"],
    "shift": ["shift", "勤務帯", "シフト", "直", "直区分", "班"],
    "issue": ["issue", "failure", "problem", "故障", "不具合", "異常内容", "事象", "故障内容", "現象"],
    "action": ["action", "countermeasure", "repair", "対策", "処置", "修理内容", "対応", "処置内容", "対策内容"],
    "current_a": ["current_a", "current", "amp", "ampere", "電流", "電流値", "溶接電流", "電流a"],
    "temperature_c": ["temperature_c", "temperature", "temp", "温度", "設備温度", "温度c", "温度℃"],
    "vibration_mm_s": ["vibration_mm_s", "vibration", "振動", "振動値", "振動速度"],
    "pressure_mpa": ["pressure_mpa", "pressure", "圧力", "加圧力", "圧力mpa"],
    "torque_nm": ["torque_nm", "torque", "トルク", "締付トルク", "締付値"],
}

DISPLAY_LABELS = {
    "vehicle_id": "製品/車両ID", "result": "OK/NG判定", "defect_type": "不具合種別",
    "inspection_item": "検査項目", "value": "測定値", "lower_limit": "規格下限",
    "upper_limit": "規格上限", "timestamp": "タイムスタンプ", "process": "工程",
    "equipment_id": "設備ID", "start_time": "開始時刻", "end_time": "終了時刻",
    "part_lot": "部品ロット", "part_no": "部品番号", "operator": "作業者",
    "shift": "シフト", "issue": "故障/異常内容", "action": "対策/処置",
    "current_a": "電流[A]", "temperature_c": "温度[℃]", "vibration_mm_s": "振動[mm/s]",
    "pressure_mpa": "圧力[MPa]", "torque_nm": "トルク[Nm]",
}

ROLE_HINTS = {
    "quality": ["quality", "inspection", "qc", "検査", "品質", "不良", "判定", "測定", "出来栄え"],
    "process": ["process", "trace", "history", "工程", "履歴", "トレース", "実績", "通過"],
    "equipment_logs": ["sensor", "equipment", "machine", "log", "設備", "センサ", "ログ", "稼働", "監視"],
    "maintenance": ["maintenance", "repair", "保全", "修理", "メンテ", "点検", "故障"],
    "parts": ["part", "lot", "部品", "ロット", "材料", "品番"],
}

ROLE_REQUIRED = {
    "quality": {"vehicle_id", "result"},
    "process": {"vehicle_id", "equipment_id"},
    "equipment_logs": {"equipment_id", "timestamp"},
    "maintenance": {"equipment_id", "issue"},
    "parts": {"vehicle_id", "part_lot"},
}

ROLE_OPTIONAL = {
    "quality": {"defect_type", "inspection_item", "value", "lower_limit", "upper_limit", "timestamp", "equipment_id", "process"},
    "process": {"process", "start_time", "end_time", "timestamp", "part_lot", "operator", "shift"},
    "equipment_logs": {"current_a", "temperature_c", "vibration_mm_s", "pressure_mpa", "torque_nm", "process"},
    "maintenance": {"action", "timestamp", "part_no"},
    "parts": {"part_no", "timestamp", "process"},
}

JOIN_KEYS = ["vehicle_id", "equipment_id", "part_lot", "part_no", "process", "timestamp"]
RESULT_TOKENS = {"ok", "ng", "nok", "pass", "fail", "failed", "合格", "不合格", "良", "不良", "正常", "異常", "○", "×", "0", "1"}


def _canon(value: Any) -> str:
    s = str(value).strip().lower()
    s = re.sub(r"[\s\-_()/\\\[\]（）【】:：.・]+", "", s)
    return s


_ALIAS_LOOKUP: dict[str, str] = {}
for target, aliases in ALIASES.items():
    for alias in aliases + [target]:
        _ALIAS_LOOKUP[_canon(alias)] = target


def _safe_value(v: Any) -> Any:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, (str, int, float, bool)):
        return v
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    return str(v)


def _load_memory() -> dict[str, Any]:
    if not SCHEMA_MEMORY.exists():
        return {"tables": {}, "learned_aliases": {}, "accepted_joins": []}
    try:
        obj = json.loads(SCHEMA_MEMORY.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("invalid schema memory")
        obj.setdefault("tables", {})
        obj.setdefault("learned_aliases", {})
        obj.setdefault("accepted_joins", [])
        return obj
    except Exception:
        return {"tables": {}, "learned_aliases": {}, "accepted_joins": []}


def schema_memory() -> dict[str, Any]:
    return _load_memory()


def _save_memory(obj: dict[str, Any]) -> None:
    SCHEMA_MEMORY.parent.mkdir(parents=True, exist_ok=True)
    tmp = SCHEMA_MEMORY.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SCHEMA_MEMORY)


def save_schema_review(table_key: str, mapping: dict[str, str | None], role: str | None = None, learn: bool = True) -> dict[str, Any]:
    mem = _load_memory()
    cleaned = {str(k): (str(v) if v else None) for k, v in mapping.items()}
    entry = mem["tables"].setdefault(table_key, {})
    entry["mapping"] = cleaned
    if role is not None:
        entry["role"] = role or None
    if learn:
        for raw, canonical in cleaned.items():
            if canonical:
                mem["learned_aliases"][_canon(raw)] = canonical
    _save_memory(mem)
    return mem


def reset_schema_review_field(table_key: str, raw: str, unlearn: bool = True) -> dict[str, Any]:
    """Remove an explicit per-table mapping and optionally the learned alias."""
    mem = _load_memory()
    entry = mem.get("tables", {}).get(table_key)
    if isinstance(entry, dict):
        mapping = entry.get("mapping")
        if isinstance(mapping, dict):
            mapping.pop(raw, None)
    if unlearn:
        mem.get("learned_aliases", {}).pop(_canon(raw), None)
    _save_memory(mem)
    return mem


def save_join_review(join_id: str, accepted: bool) -> dict[str, Any]:
    mem = _load_memory()
    accepted_ids = set(mem.get("accepted_joins", []))
    if accepted:
        accepted_ids.add(join_id)
    else:
        accepted_ids.discard(join_id)
    mem["accepted_joins"] = sorted(accepted_ids)
    _save_memory(mem)
    return mem


def _read_csv(path: Path) -> pd.DataFrame:
    last = None
    for enc in ["utf-8-sig", "utf-8", "cp932", "shift_jis"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as exc:
            last = exc
    raise last or RuntimeError("CSV read failed")


def _read_tables(path: Path) -> list[tuple[str | None, pd.DataFrame]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return [(None, _read_csv(path))]
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        book = pd.ExcelFile(path)
        return [(sheet, pd.read_excel(path, sheet_name=sheet)) for sheet in book.sheet_names]
    if suffix == ".json":
        obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        if isinstance(obj, list):
            return [(None, pd.DataFrame(obj))]
        if isinstance(obj, dict):
            tables = []
            for k, v in obj.items():
                if isinstance(v, list) and (not v or isinstance(v[0], dict)):
                    tables.append((str(k), pd.DataFrame(v)))
            return tables or [(None, pd.DataFrame([obj]))]
    return []


def _series_profile(series: pd.Series, max_examples: int = 20) -> dict[str, Any]:
    s = series
    nonnull = s.dropna()
    rows = len(s)
    unique = int(nonnull.nunique(dropna=True)) if len(nonnull) else 0
    null_rate = float(s.isna().mean()) if rows else 1.0
    unique_ratio = float(unique / max(1, len(nonnull))) if len(nonnull) else 0.0
    examples = [_safe_value(v) for v in nonnull.head(max_examples).tolist()]
    strvals = nonnull.astype(str).str.strip() if len(nonnull) else pd.Series(dtype=str)
    lower_vals = {x.lower() for x in strvals.head(200).tolist()}

    numeric = pd.to_numeric(nonnull, errors="coerce") if len(nonnull) else pd.Series(dtype=float)
    numeric_ratio = float(numeric.notna().mean()) if len(nonnull) else 0.0
    numeric_good = numeric.dropna()

    # Datetime inference is intentionally conservative for pure integer columns.
    dt_ratio = 0.0
    if len(nonnull) and numeric_ratio < 0.95:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                parsed = pd.to_datetime(nonnull, errors="coerce")
            dt_ratio = float(parsed.notna().mean())
        except Exception:
            dt_ratio = 0.0

    if dt_ratio >= 0.8:
        semantic_type = "datetime"
    elif numeric_ratio >= 0.9:
        semantic_type = "numeric"
    elif unique <= max(20, int(len(nonnull) * 0.08)):
        semantic_type = "categorical"
    else:
        semantic_type = "string"

    id_like_ratio = 0.0
    leading_zero_ratio = 0.0
    if len(strvals):
        id_pat = strvals.str.match(r"^[A-Za-z]{0,8}[-_ ]?\d{2,}[A-Za-z0-9_-]*$") | strvals.str.match(r"^[A-Za-z0-9_-]{4,24}$")
        id_like_ratio = float(id_pat.mean())
        leading_zero_ratio = float(strvals.str.match(r"^0\d+").mean())

    result_ratio = 0.0
    if lower_vals:
        result_ratio = sum(1 for x in lower_vals if x in RESULT_TOKENS) / max(1, len(lower_vals))

    out = {
        "dtype": str(s.dtype),
        "semantic_type": semantic_type,
        "rows": rows,
        "null_rate": round(null_rate, 4),
        "unique_count": unique,
        "unique_ratio": round(unique_ratio, 4),
        "numeric_ratio": round(numeric_ratio, 4),
        "datetime_ratio": round(dt_ratio, 4),
        "id_like_ratio": round(id_like_ratio, 4),
        "leading_zero_ratio": round(leading_zero_ratio, 4),
        "result_token_ratio": round(result_ratio, 4),
        "examples": examples,
    }
    if len(numeric_good):
        out.update({
            "min": _safe_value(float(numeric_good.min())),
            "max": _safe_value(float(numeric_good.max())),
            "median": _safe_value(float(numeric_good.median())),
            "mean": _safe_value(float(numeric_good.mean())),
        })
    return out


def _name_similarity(raw: str, canonical: str) -> tuple[float, str]:
    key = _canon(raw)
    if not key:
        return 0.0, ""
    if key == _canon(canonical):
        return 0.99, "canonical name match"
    aliases = ALIASES.get(canonical, []) + [canonical]
    canon_aliases = [_canon(a) for a in aliases]
    if key in canon_aliases:
        return 0.985, "known manufacturing alias"
    contains = [a for a in canon_aliases if len(a) >= 2 and (a in key or key in a)]
    if contains:
        best = max(contains, key=len)
        return min(0.94, 0.84 + min(0.10, len(best) / 100)), "partial alias match"
    sim = max([SequenceMatcher(None, key, a).ratio() for a in canon_aliases] or [0.0])
    if sim >= 0.72:
        return 0.50 + 0.40 * sim, f"name similarity {sim:.2f}"
    return 0.0, ""


def _value_score(canonical: str, p: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    stype = p["semantic_type"]
    unique_ratio = float(p["unique_ratio"])
    id_like = float(p["id_like_ratio"])
    result_ratio = float(p["result_token_ratio"])
    dt_ratio = float(p["datetime_ratio"])
    numeric_ratio = float(p["numeric_ratio"])

    if canonical == "timestamp":
        if dt_ratio >= 0.9:
            score += 0.48; reasons.append("values parse as datetime")
        elif dt_ratio >= 0.6:
            score += 0.30; reasons.append("many values parse as datetime")
    elif canonical == "result":
        if result_ratio >= 0.75:
            score += 0.50; reasons.append("values look like OK/NG judgement")
        elif stype == "categorical" and p["unique_count"] <= 8:
            score += 0.12; reasons.append("low-cardinality category")
    elif canonical == "vehicle_id":
        if unique_ratio >= 0.75 and id_like >= 0.55:
            score += 0.38; reasons.append("high-uniqueness ID pattern")
        elif unique_ratio >= 0.85:
            score += 0.22; reasons.append("high-uniqueness column")
        if p["leading_zero_ratio"] > 0.3:
            score += 0.08; reasons.append("leading zeros suggest identifier")
    elif canonical == "equipment_id":
        if id_like >= 0.45 and 0.005 <= unique_ratio <= 0.60:
            score += 0.30; reasons.append("repeating machine-like identifier")
        elif stype == "categorical" and p["unique_count"] >= 2:
            score += 0.16; reasons.append("repeating categorical identifier")
    elif canonical in {"process", "part_lot", "part_no", "operator", "shift", "inspection_item", "defect_type", "issue", "action"}:
        if stype in {"categorical", "string"}:
            score += 0.10
        if canonical in {"part_lot", "part_no"} and id_like >= 0.4:
            score += 0.12; reasons.append("lot/part-like code pattern")
    elif canonical in {"value", "lower_limit", "upper_limit", "current_a", "temperature_c", "vibration_mm_s", "pressure_mpa", "torque_nm"}:
        if numeric_ratio >= 0.9:
            score += 0.24; reasons.append("numeric measurement values")
    elif canonical in {"start_time", "end_time"}:
        if dt_ratio >= 0.75:
            score += 0.35; reasons.append("datetime values")
    return min(0.55, score), reasons


def _infer_column(raw: str, p: dict[str, Any], learned_aliases: dict[str, str]) -> dict[str, Any]:
    key = _canon(raw)
    if key in learned_aliases and learned_aliases[key] in ALIASES:
        target = learned_aliases[key]
        return {
            "raw": raw, "canonical": target, "label": DISPLAY_LABELS.get(target, target),
            "confidence": 1.0, "status": "learned", "reasons": ["approved mapping learned for this deployment"],
            "alternatives": [], **p,
        }

    candidates = []
    for canonical in ALIASES:
        name_score, name_reason = _name_similarity(raw, canonical)
        value_bonus, value_reasons = _value_score(canonical, p)
        # Value semantics can rescue unknown headers, but never dominate a strong name mismatch.
        if name_score > 0:
            score = min(0.995, name_score * 0.82 + value_bonus * 0.55)
        else:
            score = min(0.78, value_bonus)
        reasons = ([name_reason] if name_reason else []) + value_reasons
        candidates.append((score, canonical, reasons))
    candidates.sort(reverse=True)
    best_score, best, reasons = candidates[0]
    alternatives = [{"canonical": c, "label": DISPLAY_LABELS.get(c, c), "confidence": round(float(s), 3)} for s, c, _ in candidates[1:4] if s >= 0.35]

    if best_score >= 0.95:
        status = "auto"
    elif best_score >= 0.80:
        status = "review"
    elif best_score >= 0.62:
        status = "review"
    else:
        status = "unresolved"
        best = None
    return {
        "raw": raw,
        "canonical": best,
        "label": DISPLAY_LABELS.get(best, best) if best else "未解釈",
        "confidence": round(float(best_score), 3),
        "status": status,
        "reasons": reasons or ["insufficient semantic evidence"],
        "alternatives": alternatives,
        **p,
    }


def infer_semantic_mapping(df: pd.DataFrame, source: str = "", sheet: str | None = None) -> tuple[dict[str, str], dict[str, float], list[dict[str, Any]], bool, bool]:
    mem = _load_memory()
    table_key = f"{source}::{sheet or ''}"
    table_override = mem.get("tables", {}).get(table_key, {})
    learned_aliases = mem.get("learned_aliases", {})
    override_mapping = table_override.get("mapping", {}) if isinstance(table_override, dict) else {}

    profiles: list[dict[str, Any]] = []
    for col in [str(c).strip() for c in df.columns]:
        p = _series_profile(df[col])
        inf = _infer_column(col, p, learned_aliases)
        if col in override_mapping:
            chosen = override_mapping[col]
            inf["canonical"] = chosen
            inf["label"] = DISPLAY_LABELS.get(chosen, chosen) if chosen else "未使用"
            inf["confidence"] = 1.0
            inf["status"] = "approved"
            inf["reasons"] = ["user-approved table mapping"]
        profiles.append(inf)

    # Relationship reasoning: measurement bounded by upper/lower spec is a strong signal.
    name_to_inf = {x["raw"]: x for x in profiles}
    numeric_cols = [x for x in profiles if x["numeric_ratio"] >= 0.9]
    inferred_fields = {x["canonical"] for x in profiles if x["canonical"]}
    if "upper_limit" in inferred_fields and "lower_limit" in inferred_fields:
        for x in numeric_cols:
            if x["canonical"] is None and x["unique_ratio"] > 0.05:
                x["canonical"] = "value"
                x["label"] = DISPLAY_LABELS["value"]
                x["confidence"] = max(float(x["confidence"]), 0.72)
                x["status"] = "review"
                x["reasons"] = list(x["reasons"]) + ["numeric column alongside upper/lower specification limits"]
                break

    # Optional approved/internal LLM enhancement for unresolved/low-confidence columns.
    # The local semantic engine remains authoritative unless the LLM is materially more confident.
    try:
        from .schema_llm import enhance as llm_enhance
        llm_rows = llm_enhance(f"{source}::{sheet or ''}", profiles, DISPLAY_LABELS)
    except Exception:
        llm_rows = {}
    for x in profiles:
        lr = llm_rows.get(x["raw"])
        if not lr:
            continue
        llm_conf = float(lr.get("confidence", 0))
        llm_target = lr.get("canonical")
        if llm_target and llm_target in ALIASES and llm_conf >= max(0.80, float(x.get("confidence", 0)) + 0.08):
            x["canonical"] = llm_target
            x["label"] = DISPLAY_LABELS.get(llm_target, llm_target)
            x["confidence"] = round(llm_conf, 3)
            x["status"] = "auto" if llm_conf >= 0.95 else "review"
            x["reasons"] = list(x.get("reasons", [])) + ["approved/internal LLM: " + str(lr.get("reason") or "semantic inference")]

    # One raw column per canonical field. Keep the highest-confidence interpretation.
    by_canonical: dict[str, list[dict[str, Any]]] = {}
    for x in profiles:
        if x["canonical"]:
            by_canonical.setdefault(x["canonical"], []).append(x)
    for canonical, xs in by_canonical.items():
        if len(xs) <= 1:
            continue
        xs.sort(key=lambda z: float(z["confidence"]), reverse=True)
        for loser in xs[1:]:
            if loser["status"] not in {"approved", "learned"}:
                loser["alternatives"] = [{"canonical": canonical, "label": DISPLAY_LABELS.get(canonical, canonical), "confidence": loser["confidence"]}] + loser.get("alternatives", [])[:2]
                loser["canonical"] = None
                loser["label"] = "未解釈"
                loser["status"] = "unresolved"
                loser["reasons"] = list(loser["reasons"]) + ["another column is a stronger match for this semantic field"]

    mapping = {x["raw"]: x["canonical"] for x in profiles if x["canonical"] and float(x["confidence"]) >= 0.62}
    confidence = {x["raw"]: float(x["confidence"]) for x in profiles if x["canonical"]}
    review_required = any(x["status"] in {"review", "unresolved"} for x in profiles)
    override_applied = bool(override_mapping)
    return mapping, confidence, profiles, review_required, override_applied


def infer_column_mapping(columns: list[str]) -> dict[str, str]:
    """Compatibility helper for callers that only have headers.

    Header-only inference intentionally avoids value-based guesses. Full table scans use
    infer_semantic_mapping() and are substantially stronger.
    """
    df = pd.DataFrame(columns=columns)
    mapping, _, _, _, _ = infer_semantic_mapping(df)
    return mapping


@dataclass
class TableProfile:
    source: str
    sheet: str | None
    columns: list[str]
    mapping: dict[str, str]
    inferred_role: str | None
    role_score: float
    rows: int
    sample: dict[str, Any] = field(default_factory=dict)
    mapping_confidence: dict[str, float] = field(default_factory=dict)
    column_profiles: list[dict[str, Any]] = field(default_factory=list)
    role_candidates: list[dict[str, Any]] = field(default_factory=list)
    compatible_roles: list[str] = field(default_factory=list)
    review_required: bool = False
    override_applied: bool = False

    @property
    def label(self) -> str:
        return f"{self.source}::{self.sheet}" if self.sheet else self.source

    @property
    def table_key(self) -> str:
        return f"{self.source}::{self.sheet or ''}"


def _role_score(source: str, sheet: str | None, mapping: dict[str, str], mapping_conf: dict[str, float], role: str) -> tuple[float, list[str]]:
    canonical_cols = set(mapping.values())
    req = ROLE_REQUIRED[role]
    opt = ROLE_OPTIONAL[role]
    req_scores = []
    for field in req:
        raws = [r for r, c in mapping.items() if c == field]
        req_scores.append(max([mapping_conf.get(r, 0.0) for r in raws] or [0.0]))
    req_coverage = sum(1 for x in req_scores if x >= 0.62) / max(1, len(req))
    req_conf = float(np.mean(req_scores)) if req_scores else 0.0
    optional_count = len(opt & canonical_cols)
    optional_bonus = min(0.20, optional_count * 0.035)
    name = f"{source} {sheet or ''}".lower()
    name_bonus = 0.12 if any(h.lower() in name for h in ROLE_HINTS[role]) else 0.0
    score = min(1.0, req_coverage * 0.55 + req_conf * 0.25 + optional_bonus + name_bonus)
    if role == "equipment_logs" and not ({"current_a", "temperature_c", "vibration_mm_s", "pressure_mpa", "torque_nm"} & canonical_cols):
        score = min(score, 0.49)
    reasons = [f"required semantic coverage {req_coverage*100:.0f}%", f"{optional_count} optional fields"]
    if name_bonus:
        reasons.append("file/sheet name supports role")
    return score, reasons


def _scan_one_path(path: Path, mem: dict) -> tuple[list[TableProfile], list[str]]:
    path_profiles: list[TableProfile] = []
    path_warnings: list[str] = []
    try:
        for sheet, df in _read_tables(path):
            cols = [str(c).strip() for c in df.columns]
            mapping, conf, col_profiles, review_required, override_applied = infer_semantic_mapping(df, display_filename(path.name), sheet)
            scored = []
            for role in ROLE_REQUIRED:
                score, reasons = _role_score(display_filename(path.name), sheet, mapping, conf, role)
                scored.append({"role": role, "score": round(float(score), 3), "reasons": reasons})
            scored.sort(key=lambda x: x["score"], reverse=True)
            table_key = f"{display_filename(path.name)}::{sheet or ''}"
            role_override = mem.get("tables", {}).get(table_key, {}).get("role")
            if role_override in ROLE_REQUIRED:
                inferred, role_score = role_override, 1.0
                scored = [{"role": role_override, "score": 1.0, "reasons": ["user-approved table role"]}] + [x for x in scored if x["role"] != role_override]
            else:
                best = scored[0] if scored else {"role": None, "score": 0.0}
                inferred = best["role"] if best["score"] >= 0.55 else None
                role_score = float(best["score"])
            sample = {}
            if len(df):
                row = df.iloc[0].to_dict()
                for raw, canonical_name in mapping.items():
                    sample[canonical_name] = _safe_value(row.get(raw))
            compatible_roles = [x["role"] for x in scored if float(x["score"]) >= 0.55]
            if role_override in ROLE_REQUIRED and role_override not in compatible_roles:
                compatible_roles.insert(0, role_override)
            path_profiles.append(TableProfile(
                display_filename(path.name), sheet, cols, mapping, inferred, role_score, len(df), sample,
                mapping_confidence=conf, column_profiles=col_profiles, role_candidates=scored[:5], compatible_roles=compatible_roles,
                review_required=review_required or (inferred is None), override_applied=override_applied,
            ))
    except Exception as exc:
        path_warnings.append(f"{display_filename(path.name)}: {exc}")
    return path_profiles, path_warnings


def scan_tables(data_dir: Path) -> tuple[list[TableProfile], list[str]]:
    profiles: list[TableProfile] = []
    warnings: list[str] = []
    mem = _load_memory()
    paths = [p for p in sorted(data_dir.rglob("*")) if p.is_file() and p.suffix.lower() in STRUCTURED_EXTS]
    if len(paths) > 1:
        # Each table can trigger a blocking DeepSeek call for low-confidence columns
        # (see schema_llm.enhance). Scanning tables concurrently means those network
        # round-trips overlap instead of stacking up sequentially, which is what
        # makes startup/rebuild latency scale with the slowest table instead of the
        # sum of all of them.
        with ThreadPoolExecutor(max_workers=min(8, len(paths))) as pool:
            for path_profiles, path_warnings in pool.map(lambda p: _scan_one_path(p, mem), paths):
                profiles.extend(path_profiles)
                warnings.extend(path_warnings)
    else:
        for path in paths:
            path_profiles, path_warnings = _scan_one_path(path, mem)
            profiles.extend(path_profiles)
            warnings.extend(path_warnings)
    return profiles, warnings


def choose_role_tables(profiles: list[TableProfile]) -> dict[str, TableProfile]:
    chosen: dict[str, TableProfile] = {}
    for role in ROLE_REQUIRED:
        candidates = [p for p in profiles if p.inferred_role == role]
        if candidates:
            chosen[role] = max(candidates, key=lambda p: (p.role_score, p.rows))
    return chosen


def _find_source_path(data_dir: Path, source: str) -> Path | None:
    return resolve_source_path(data_dir, source)


def load_profile_frame(data_dir: Path, profile: TableProfile) -> pd.DataFrame:
    path = _find_source_path(data_dir, profile.source)
    if path is None:
        return pd.DataFrame()
    for sheet, df in _read_tables(path):
        if sheet == profile.sheet:
            return df.rename(columns=profile.mapping).copy()
    return pd.DataFrame()


def _value_overlap(a: pd.Series, b: pd.Series) -> tuple[float, int, int, int]:
    av = {str(x).strip().upper() for x in a.dropna().head(5000).tolist() if str(x).strip()}
    bv = {str(x).strip().upper() for x in b.dropna().head(5000).tolist() if str(x).strip()}
    if not av or not bv:
        return 0.0, len(av), len(bv), 0
    inter = len(av & bv)
    return inter / max(1, min(len(av), len(bv))), len(av), len(bv), inter


def discover_join_candidates(data_dir: Path, profiles: list[TableProfile]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    mem = _load_memory()
    accepted = set(mem.get("accepted_joins", []))
    cache: dict[str, pd.DataFrame] = {}
    for i, a in enumerate(profiles):
        if not a.mapping:
            continue
        cache[a.table_key] = load_profile_frame(data_dir, a)
        for b in profiles[i + 1:]:
            if not b.mapping:
                continue
            cache.setdefault(b.table_key, load_profile_frame(data_dir, b))
            fa, fb = cache[a.table_key], cache[b.table_key]
            common = [k for k in JOIN_KEYS if k in fa.columns and k in fb.columns]
            if not common:
                continue
            for key in common:
                if key == "timestamp":
                    # Timestamp alone is usually not a safe equi-join. Offer it as a time-window relationship.
                    confidence = 0.68
                    overlap = None
                    mode = "time_window"
                    reason = "both tables contain a timestamp; use nearest/time-window matching rather than exact equality"
                else:
                    overlap, ua, ub, inter = _value_overlap(fa[key], fb[key])
                    base = {"vehicle_id": 0.68, "equipment_id": 0.64, "part_lot": 0.62, "part_no": 0.60, "process": 0.55}.get(key, 0.55)
                    confidence = min(0.99, base + 0.28 * overlap)
                    mode = "equi_join"
                    reason = f"shared semantic key {key}; sample overlap {overlap*100:.0f}% ({inter} shared values)"
                    if overlap < 0.05 and key not in {"vehicle_id", "equipment_id"}:
                        continue
                join_id = f"{a.table_key}|{b.table_key}|{key}|{mode}"
                suggestions.append({
                    "id": join_id,
                    "left": a.table_key,
                    "right": b.table_key,
                    "left_role": a.inferred_role,
                    "right_role": b.inferred_role,
                    "key": key,
                    "label": DISPLAY_LABELS.get(key, key),
                    "mode": mode,
                    "confidence": round(float(confidence), 3),
                    "reason": reason,
                    "status": "accepted" if join_id in accepted else ("auto" if confidence >= 0.95 else "review" if confidence >= 0.80 else "suggested"),
                })
            if "equipment_id" in common and "timestamp" in common:
                join_id = f"{a.table_key}|{b.table_key}|equipment_id+timestamp|asof"
                suggestions.append({
                    "id": join_id, "left": a.table_key, "right": b.table_key,
                    "left_role": a.inferred_role, "right_role": b.inferred_role,
                    "key": "equipment_id + timestamp", "label": "設備ID＋時刻", "mode": "asof_join",
                    "confidence": 0.93, "reason": "same equipment can be aligned to the nearest sensor/event timestamp",
                    "status": "accepted" if join_id in accepted else "review",
                })
    # Deduplicate and rank.
    seen = set(); out = []
    for s in sorted(suggestions, key=lambda x: x["confidence"], reverse=True):
        if s["id"] in seen:
            continue
        seen.add(s["id"]); out.append(s)
    out = out[:100]

    # DeepSeek V4 Flash adds semantic validation/proposals on top of deterministic
    # key overlap. It never removes a local candidate and falls back silently.
    try:
        from .join_llm import enhance as enhance_joins
        out = enhance_joins(profiles, out)
    except Exception:
        pass
    return out[:100]


def catalog_as_dict(profiles: list[TableProfile]) -> list[dict[str, Any]]:
    return [
        {
            "source": p.source,
            "sheet": p.sheet,
            "table_key": p.table_key,
            "rows": p.rows,
            "columns": p.columns,
            "mapping": p.mapping,
            "mapping_confidence": {k: round(float(v), 3) for k, v in p.mapping_confidence.items()},
            "column_profiles": p.column_profiles,
            "role": p.inferred_role,
            "role_score": round(p.role_score, 3),
            "role_candidates": p.role_candidates,
            "compatible_roles": p.compatible_roles,
            "review_required": p.review_required,
            "override_applied": p.override_applied,
            "sample": {k: _safe_value(v) for k, v in p.sample.items()},
        }
        for p in profiles
    ]


def choose_role_tables_multi(profiles: list[TableProfile], min_score: float = 0.55) -> dict[str, list[TableProfile]]:
    out: dict[str, list[TableProfile]] = {}
    for role in ROLE_REQUIRED:
        candidates = []
        for p in profiles:
            role_score = next((float(x.get("score", 0)) for x in p.role_candidates if x.get("role") == role), 0.0)
            if role in p.compatible_roles and role_score >= min_score:
                candidates.append((role_score, p))
        candidates.sort(key=lambda x: (x[0], x[1].rows), reverse=True)
        out[role] = [p for _, p in candidates]
    return out


def load_role_frame(data_dir: Path, profiles: list[TableProfile]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for prof in profiles:
        df = load_profile_frame(data_dir, prof)
        if df.empty:
            continue
        df = df.copy()
        df["_source_file"] = prof.source
        df["_source_sheet"] = prof.sheet or ""
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)
