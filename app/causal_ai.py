from __future__ import annotations


def dowhy_available() -> bool:
    try:
        import dowhy  # type: ignore  # noqa:F401
        return True
    except Exception:
        return False


def readiness_note() -> dict:
    return {
        "available": dowhy_available(),
        "purpose": "相関ランキングの次段として、介入/交絡を明示した因果効果推定を行うための拡張口",
        "warning": "因果推論はDAG・交絡変数・介入定義が必要。自動相関を因果と表示しない。",
    }
