"""Tests for ingestion slice naming and composite labels."""
from __future__ import annotations

from pathlib import Path

from Analyzer.player_composite import player_impact_label
from ingestion.utils.slice_names import parse_raw_slice_filename, slice_filename


def test_legacy_dash_filename_parses_as_base():
    parsed = parse_raw_slice_filename(Path("dash_regular_season_pergame.parquet"))
    assert parsed == ("dash", "Regular Season", "Base", "PerGame")


def test_extended_dash_filename_parses_measure_and_per_mode():
    parsed = parse_raw_slice_filename(
        Path("dash_playoffs_advanced_per100possessions.parquet")
    )
    assert parsed == ("dash", "Playoffs", "Advanced", "Per100Possessions")


def test_slice_filename_round_trip():
    name = slice_filename("dash", "Regular Season", "Usage", "Per36")
    assert name == "dash_regular_season_usage_per36.parquet"


def test_player_impact_label_star_tier():
    profile = player_impact_label(net_rating=6.0, usg_pct=30.0, pie=14.0, gp=60)
    assert profile["label"] == "Primary Creator"
    assert profile["tier"] == 5
