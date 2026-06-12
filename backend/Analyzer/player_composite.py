"""NBA-native player impact labels from staged advanced / estimated metrics."""
from __future__ import annotations

from typing import Any


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:  # NaN
        return None
    return out


def player_impact_label(
    *,
    net_rating: float | None = None,
    usg_pct: float | None = None,
    pie: float | None = None,
    gp: float | None = None,
) -> dict[str, Any]:
    """
    Rule-based tier label using NBA official impact proxies (not third-party EPM/DARKO).

    Returns headline_score (PIE preferred, else scaled net rating), label, and tier rank.
    """
    net = _to_float(net_rating)
    usg = _to_float(usg_pct)
    pie = _to_float(pie)
    games = _to_float(gp) or 0.0

    if games < 10:
        return {
            "label": "Small Sample",
            "tier": 0,
            "headline_metric": "PIE",
            "headline_score": pie,
            "net_rating": net,
            "usg_pct": usg,
            "pie": pie,
        }

    headline_score = pie
    headline_metric = "PIE"
    if headline_score is None and net is not None:
        headline_score = round(net / 10.0, 2)
        headline_metric = "NET_RATING"

    label = "Rotation Player"
    tier = 3

    if net is not None and usg is not None:
        if net >= 5.0 and usg >= 28.0:
            label, tier = "Primary Creator", 5
        elif net >= 3.0 and usg >= 24.0:
            label, tier = "Star Offense", 4
        elif net >= 2.0:
            label, tier = "Two-Way Starter", 4
        elif net >= 0.0:
            label, tier = "Solid Starter", 3
        elif net >= -2.0:
            label, tier = "Rotation Player", 2
        else:
            label, tier = "Bench / Depth", 1
    elif pie is not None:
        if pie >= 15.0:
            label, tier = "High Impact", 5
        elif pie >= 12.0:
            label, tier = "Strong Contributor", 4
        elif pie >= 10.0:
            label, tier = "Rotation Player", 3
        elif pie >= 8.0:
            label, tier = "Role Player", 2
        else:
            label, tier = "Bench / Depth", 1

    return {
        "label": label,
        "tier": tier,
        "headline_metric": headline_metric,
        "headline_score": headline_score,
        "net_rating": net,
        "usg_pct": usg,
        "pie": pie,
    }
