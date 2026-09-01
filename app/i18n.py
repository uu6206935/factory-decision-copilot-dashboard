from __future__ import annotations

import re

ROLE_LABELS = {
    "quality": "品質",
    "process": "工程",
    "equipment_logs": "設備ログ",
    "maintenance": "保全履歴",
    "parts": "部品・ロット",
    "documents": "文書",
    "vision": "画像検査",
    "acoustic": "音響",
    "unknown": "未判定",
}

STATUS_LABELS = {
    "pending": "未承認",
    "approved": "承認済み",
    "held": "保留",
    "rejected": "却下",
    "accepted": "承認済み",
    "auto": "自動候補",
    "review": "要確認",
    "suggested": "候補",
    "unresolved": "未解釈",
    "learned": "学習済み",
    "active": "稼働中",
    "waiting": "データ待ち",
    "waiting_data": "データ待ち",
    "ready": "準備完了",
    "pass": "正常",
    "warn": "注意",
    "warning": "注意",
    "fail": "異常",
    "blocked": "ブロック",
    "critical": "重大",
    "high": "高",
    "medium": "中",
    "low": "低",
    "on": "稼働",
    "off": "停止",
}

MODE_LABELS = {
    "root_cause": "原因探索",
    "adaptive": "自動適応分析",
    "rag": "文書検索",
    "equipment": "設備分析",
    "quality": "品質分析",
    "process": "工程分析",
    "maintenance": "保全分析",
    "parts": "部品分析",
}

SEMANTIC_TYPE_LABELS = {
    "datetime": "日時",
    "numeric": "数値",
    "categorical": "カテゴリ",
    "string": "文字列",
    "boolean": "真偽値",
}

DTYPE_REPLACEMENTS = {
    "object": "文字列/混在",
    "string": "文字列",
    "float64": "小数",
    "float32": "小数",
    "int64": "整数",
    "int32": "整数",
    "bool": "真偽値",
    "datetime64[ns]": "日時",
}

JOIN_MODE_LABELS = {
    "equi_join": "等価結合",
    "EQUI_JOIN": "等価結合",
    "asof_join": "時刻近傍結合",
    "ASOF_JOIN": "時刻近傍結合",
    "time_window": "時間窓結合",
    "TIME_WINDOW": "時間窓結合",
}

KIND_LABELS = {
    "file": "ファイル",
    "table": "テーブル",
    "column": "列",
    "join": "結合",
    "module": "分析",
    "maps": "意味付け",
    "enables": "分析を有効化",
    "supports_analysis": "分析を支援",
    "process_link": "工程関連",
    "equipment_correlation": "設備関連",
    "sensor": "センサ",
    "maintenance": "保全",
    "parts": "部品",
    "document": "文書",
    "vision": "画像",
    "quality": "品質",
    "process": "工程",
    "equipment": "設備",
    "part_lot": "部品ロット",
}

SIGNAL_LABELS = {
    "quality": "品質",
    "process": "工程",
    "equipment_logs": "設備ログ",
    "maintenance": "保全",
    "parts": "部品",
    "documents": "文書",
    "vision": "画像",
    "acoustic": "音響",
}

DATA_QUALITY_LABELS = {
    "ok": "正常",
    "skip": "対象外",
    "warn": "注意",
    "fail": "異常",
    "files": "ファイル",
    "tables": "テーブル",
    "chunks": "検索断片",
    "available_roles": "利用可能データ種別",
    "adaptive_mode": "自動適応モード",
}

REASON_EXACT = {
    "values parse as datetime": "値の多くが日時として解釈できます",
    "many values parse as datetime": "日時として解釈できる値が多数あります",
    "values look like OK/NG judgement": "値がOK/NGなどの品質判定に見えます",
    "low-cardinality category": "種類数が少ないカテゴリ列です",
    "high-uniqueness ID pattern": "一意性が高くID形式に見えます",
    "high-uniqueness column": "値の一意性が高い列です",
    "leading zeros suggest identifier": "先頭ゼロを含み識別子形式に見えます",
    "repeating machine-like identifier": "設備番号のような識別子が繰り返されています",
    "repeating categorical identifier": "カテゴリ識別子が繰り返されています",
    "lot/part-like code pattern": "ロット/部品番号のようなコード形式です",
    "numeric measurement values": "数値の測定値に見えます",
    "datetime values": "日時値として解釈できます",
    "approved mapping learned for this deployment": "この環境で承認済みの対応として学習されています",
    "insufficient semantic evidence": "意味を確定する根拠が不足しています",
    "user-approved table mapping": "ユーザーが承認した列対応です",
    "numeric column alongside upper/lower specification limits": "規格上限・下限と並ぶ数値列のため測定値と判断しました",
    "another column is a stronger match for this semantic field": "同じ意味に対して、より適合度の高い別列があります",
    "file/sheet name supports role": "ファイル名/シート名がこのデータ種別を示唆しています",
    "user-approved table role": "ユーザーが承認したデータ種別です",
    "both tables contain a timestamp; use nearest/time-window matching rather than exact equality": "両テーブルに時刻があるため、完全一致ではなく近傍時刻/時間窓での結合を推奨します",
    "same equipment can be aligned to the nearest sensor/event timestamp": "同じ設備を最も近いセンサ/イベント時刻で対応付けできます",
    "semantic inference": "意味推定",
    "semantic validation": "意味整合性の確認",
    "DeepSeek Flash semantic inference": "DeepSeek Flashによる意味推定",
}


def ja_role(value):
    s = str(value or "")
    return ROLE_LABELS.get(s, s or "未判定")


def ja_status(value):
    s = str(value or "")
    return STATUS_LABELS.get(s.lower(), STATUS_LABELS.get(s, s or "—"))


def ja_mode(value):
    s = str(value or "")
    return MODE_LABELS.get(s, s or "—")


def ja_semantic_type(value):
    s = str(value or "")
    return SEMANTIC_TYPE_LABELS.get(s, s or "—")


def ja_dtype(value):
    s = str(value or "")
    return DTYPE_REPLACEMENTS.get(s, s or "—")


def ja_join_mode(value):
    s = str(value or "")
    return JOIN_MODE_LABELS.get(s, s or "—")


def ja_kind(value):
    s = str(value or "")
    return KIND_LABELS.get(s, s or "—")


def ja_signal(value):
    s = str(value or "")
    return SIGNAL_LABELS.get(s, s or "—")


def ja_data_quality_key(value):
    s = str(value or "")
    return DATA_QUALITY_LABELS.get(s, s)


def ja_reason(value):
    s = str(value or "")
    if not s:
        return "—"
    if s in REASON_EXACT:
        return REASON_EXACT[s]
    # Join/relation reason patterns.
    m = re.fullmatch(r"compatible: (.+)", s)
    if m:
        raw = [x.strip() for x in m.group(1).split(",") if x.strip()]
        if raw == ["none"]:
            return "互換候補なし"
        return "互換候補: " + " / ".join(ja_role(x) for x in raw)
    m = re.fullmatch(r"shared semantic key ([^;]+); sample overlap ([0-9.]+)% \((\d+) shared values\)", s)
    if m:
        return f"共通の意味キー {ja_term(m.group(1).strip())}。サンプル値の重複率 {m.group(2)}%（共通値 {m.group(3)}件）"
    m = re.fullmatch(r"shared semantic key ([^;]+)", s)
    if m:
        return f"共通の意味キー {ja_term(m.group(1).strip())}"
    m = re.fullmatch(r"sample overlap ([0-9.]+)% \((\d+) shared values\)", s)
    if m:
        return f"サンプル値の重複率 {m.group(1)}%（共通値 {m.group(2)}件）"
    if s == "semantic validation":
        return "意味整合性の確認"
    m = re.fullmatch(r"required semantic coverage ([0-9.]+)%", s)
    if m:
        return f"必須項目の意味カバー率 {m.group(1)}%"
    m = re.fullmatch(r"(\d+) optional fields", s)
    if m:
        return f"任意項目 {m.group(1)}個を検出"
    m = re.fullmatch(r"approved/internal LLM: (.+)", s)
    if m:
        return "DeepSeek Flash補強: " + ja_reason(m.group(1))
    m = re.fullmatch(r"DeepSeek Flash: (.+)", s)
    if m:
        return "DeepSeek Flash判定: " + ja_reason(m.group(1))
    m = re.fullmatch(r"DeepSeek Flash semantic proposal: (.+)", s)
    if m:
        return "DeepSeek Flashによる関連付け候補: " + ja_reason(m.group(1))
    # Translate compound reasons separated by semicolons without damaging IDs.
    if ";" in s:
        return "；".join(ja_reason(part.strip()) for part in s.split(";") if part.strip())
    return s

CANONICAL_LABELS = {
    "vehicle_id": "製品/車両ID", "result": "OK/NG判定", "defect_type": "不具合種別",
    "inspection_item": "検査項目", "value": "測定値", "lower_limit": "規格下限",
    "upper_limit": "規格上限", "timestamp": "タイムスタンプ", "process": "工程",
    "equipment_id": "設備ID", "start_time": "開始時刻", "end_time": "終了時刻",
    "part_lot": "部品ロット", "part_no": "部品番号", "operator": "作業者",
    "shift": "シフト", "issue": "故障/異常内容", "action": "対策/処置",
    "current_a": "電流[A]", "temperature_c": "温度[℃]", "vibration_mm_s": "振動[mm/s]",
    "pressure_mpa": "圧力[MPa]", "torque_nm": "トルク[Nm]",
    "rms": "RMS実効値", "crest_factor": "クレストファクタ",
    "spectral_centroid_hz": "スペクトル重心[Hz]", "dominant_freq_hz": "卓越周波数[Hz]",
    "high_frequency_ratio": "高周波比率", "healthy": "正常", "unknown": "未判定",
    "contains": "含む", "join_key": "結合キー", "join_table": "結合テーブル",
}


def ja_term(value):
    s = str(value or "")
    for mapping in (ROLE_LABELS, STATUS_LABELS, MODE_LABELS, SEMANTIC_TYPE_LABELS, JOIN_MODE_LABELS, KIND_LABELS, SIGNAL_LABELS, CANONICAL_LABELS):
        if s in mapping:
            return mapping[s]
        if s.lower() in mapping:
            return mapping[s.lower()]
    return s or "—"


def ja_terms(values, sep=" / "):
    if values is None:
        return "—"
    if isinstance(values, str):
        values = [values]
    return sep.join(ja_term(v) for v in values) if values else "—"


def ja_mapping(value):
    if not value:
        return "—"
    if isinstance(value, dict):
        return " / ".join(f"{k} → {CANONICAL_LABELS.get(str(v), str(v)) if v is not None else '未使用'}" for k, v in value.items())
    return str(value)
