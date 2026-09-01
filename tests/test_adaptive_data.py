from pathlib import Path
import pandas as pd

from app.analysis import analyze
from app.capabilities import detect_capabilities


def write_csv(path: Path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def test_quality_only_mode(tmp_path):
    write_csv(tmp_path / "品質.csv", [
        {"車両番号":"V-1","判定":"OK","不具合内容":""},
        {"車両番号":"V-2","判定":"NG","不具合内容":"キズ"},
        {"車両番号":"V-3","判定":"NG","不具合内容":"キズ"},
    ])
    caps=detect_capabilities(tmp_path)
    assert caps["signals"]["quality"] is True
    assert caps["signals"]["process"] is False
    assert caps["modules"]["quality_trends"]["enabled"] is True
    assert caps["modules"]["root_cause"]["enabled"] is False
    r=analyze("品質NG傾向を分析して",tmp_path)
    assert r.mode == "adaptive"
    assert "quality_trends" in r.active_modules
    assert r.candidates


def test_sensor_only_mode(tmp_path):
    rows=[]
    for i in range(20):
        rows.append({"設備番号":"EQ-1","日時":f"2026-08-24 08:{i:02d}:00","電流値":100 if i<16 else 125+i})
    write_csv(tmp_path / "設備ログ.csv", rows)
    caps=detect_capabilities(tmp_path)
    assert caps["modules"]["sensor_monitoring"]["enabled"] is True
    assert caps["modules"]["predictive_watch"]["enabled"] is True
    assert caps["modules"]["quality_trends"]["enabled"] is False
    r=analyze("設備ログから異常を見て",tmp_path)
    assert r.mode == "adaptive"
    assert any(c.category == "equipment" for c in r.candidates)


def test_process_only_mode(tmp_path):
    rows=[]
    for v in range(4):
        rows += [
            {"車両番号":f"V-{v}","設備番号":"EQ-A","開始時刻":"2026-08-24 08:00:00","終了時刻":"2026-08-24 08:01:00"},
            {"車両番号":f"V-{v}","設備番号":"EQ-B","開始時刻":"2026-08-24 08:01:00","終了時刻":f"2026-08-24 08:0{3+v}:00"},
        ]
    write_csv(tmp_path / "工程履歴.csv", rows)
    caps=detect_capabilities(tmp_path)
    assert caps["modules"]["process_intelligence"]["enabled"] is True
    r=analyze("工程のボトルネックを分析",tmp_path)
    assert "process_intelligence" in r.active_modules
    assert any(c.category == "process_bottleneck" for c in r.candidates)


def test_maintenance_only_mode(tmp_path):
    write_csv(tmp_path / "保全履歴.csv", [
        {"設備番号":"EQ-X","故障":"ベアリング摩耗","対応":"交換"},
        {"設備番号":"EQ-X","故障":"ベアリング摩耗","対応":"交換"},
        {"設備番号":"EQ-Y","故障":"センサ異常","対応":"校正"},
    ])
    caps=detect_capabilities(tmp_path)
    assert caps["modules"]["maintenance_intelligence"]["enabled"] is True
    r=analyze("保全履歴から再発を見て",tmp_path)
    assert any(c.category == "maintenance" for c in r.candidates)


def test_parts_only_mode(tmp_path):
    write_csv(tmp_path / "部品ロット.csv", [
        {"車両番号":"V-1","部品ロット":"LOT-A","部品番号":"P-01"},
        {"車両番号":"V-2","部品ロット":"LOT-B","部品番号":"P-01"},
    ])
    caps=detect_capabilities(tmp_path)
    assert caps["modules"]["part_traceability"]["enabled"] is True
    r=analyze("V-1の部品ロットを見て",tmp_path)
    assert r.vehicle_id == "V-1"
    assert any(c.category == "part_trace" for c in r.candidates)


def test_documents_only_enables_rag(tmp_path):
    (tmp_path / "手順書.md").write_text("電極摩耗時はチップを確認し交換する。",encoding="utf-8")
    caps=detect_capabilities(tmp_path, chunks=[object()])
    assert caps["modules"]["rag_assistant"]["enabled"] is True
    assert caps["modules"]["root_cause"]["enabled"] is False
    r=analyze("電極摩耗の手順を教えて",tmp_path)
    assert r.mode == "adaptive"
    assert "rag_assistant" in r.active_modules


def test_quality_and_parts_without_process_still_correlates(tmp_path):
    write_csv(tmp_path / "品質.csv", [
        {"車両番号":"V-1","判定":"NG"},{"車両番号":"V-2","判定":"NG"},{"車両番号":"V-3","判定":"OK"},{"車両番号":"V-4","判定":"OK"},
    ])
    write_csv(tmp_path / "部品ロット.csv", [
        {"車両番号":"V-1","部品ロット":"BAD"},{"車両番号":"V-2","部品ロット":"BAD"},{"車両番号":"V-3","部品ロット":"GOOD"},{"車両番号":"V-4","部品ロット":"GOOD"},
    ])
    r=analyze("品質とロットの関係を分析",tmp_path)
    assert r.mode == "adaptive"
    assert any(c.category == "part_lot" for c in r.candidates)


def test_empty_directory_does_not_crash(tmp_path, monkeypatch):
    import app.capabilities as capsmod
    monkeypatch.setattr(capsmod, "VISION_CONFIG", tmp_path / "no-camera.json")
    caps=capsmod.detect_capabilities(tmp_path)
    assert caps["ready"] is False
    r=analyze("利用可能なデータを分析",tmp_path)
    assert r.mode == "adaptive"
    assert r.candidates == []


def test_audio_only_capability(tmp_path, monkeypatch):
    import math, struct, wave
    import app.capabilities as capsmod
    monkeypatch.setattr(capsmod, "VISION_CONFIG", tmp_path / "no-camera.json")
    def make_wav(path, freq):
        sr=8000
        with wave.open(str(path),"wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            frames=b"".join(struct.pack("<h",int(10000*math.sin(2*math.pi*freq*i/sr))) for i in range(sr//2))
            w.writeframes(frames)
    make_wav(tmp_path/"normal_01.wav",300)
    make_wav(tmp_path/"anomaly_01.wav",1300)
    caps=capsmod.detect_capabilities(tmp_path)
    assert caps["signals"]["acoustic"] is True
    assert caps["modules"]["acoustic_monitoring"]["enabled"] is True
