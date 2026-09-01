from __future__ import annotations

from .models import Scenario


def compare_stop_vs_continue(
    ng_rate: float,
    baseline_ng_rate: float,
    production_rate_per_hour: float = 20.0,
    stop_minutes: float = 30.0,
    horizon_hours: float = 2.0,
) -> list[Scenario]:
    ng_rate = max(0.0, min(1.0, float(ng_rate)))
    baseline = max(0.0, min(1.0, float(baseline_ng_rate)))
    volume = production_rate_per_hour * horizon_hours
    continue_defects = volume * ng_rate
    lost_units = production_rate_per_hour * (stop_minutes / 60.0)
    # PoC assumption: maintenance brings defect rate back toward observed baseline.
    post_maintenance_volume = max(0.0, volume - lost_units)
    stop_defects = post_maintenance_volume * baseline
    return [
        Scenario(
            name="稼働継続",
            production_loss_units=0.0,
            expected_defects=continue_defects,
            expected_quality_loss_index=continue_defects,
            note=f"今後{horizon_hours:.0f}時間、現在のNG率が続くと仮定した簡易推計",
        ),
        Scenario(
            name=f"{stop_minutes:.0f}分停止して点検",
            production_loss_units=lost_units,
            expected_defects=stop_defects,
            expected_quality_loss_index=stop_defects + lost_units * 0.25,
            note="点検後にNG率が全体ベースラインまで戻ると仮定したPoCシミュレーション",
        ),
    ]
