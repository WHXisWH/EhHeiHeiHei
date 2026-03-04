import math

from parallelife.domain.decision import Decision
from parallelife.settings import Settings
from parallelife.usecases.risk_gate import enforce_spatial_rules, _haversine_m


def _settings() -> Settings:
    return Settings(app_env="test")


def test_clamp_out_of_bbox() -> None:
    """Destination outside Shibuya bbox is clamped, not rejected."""
    s = _settings()
    d = Decision(action="move", target=None, destination={"lat": 0.0, "lon": 0.0})
    result = enforce_spatial_rules(
        settings=s,
        current_lat=35.6595,
        current_lon=139.7005,
        decision=d,
        nearby_poi_ids=set(),
        nearby_building_ids=set(),
    )
    assert result.destination is not None
    assert s.shibuya_min_lat <= result.destination.lat <= s.shibuya_max_lat
    assert s.shibuya_min_lon <= result.destination.lon <= s.shibuya_max_lon


def test_clamp_too_far() -> None:
    """Move exceeding max_move_m is scaled down, direction preserved."""
    s = _settings()
    d = Decision(action="move", target=None, destination={"lat": 35.6900, "lon": 139.7200})
    result = enforce_spatial_rules(
        settings=s,
        current_lat=35.6595,
        current_lon=139.7005,
        decision=d,
        nearby_poi_ids=set(),
        nearby_building_ids=set(),
        max_move_m=300.0,
    )
    assert result.destination is not None
    dist = _haversine_m(35.6595, 139.7005, result.destination.lat, result.destination.lon)
    assert dist <= 300.0 + 1.0  # allow 1m float tolerance


def test_nullify_target_not_nearby() -> None:
    """Unknown target is cleared instead of raising."""
    s = _settings()
    d = Decision(action="move", target="poi999", destination={"lat": 35.6595, "lon": 139.7005})
    result = enforce_spatial_rules(
        settings=s,
        current_lat=35.6595,
        current_lon=139.7005,
        decision=d,
        nearby_poi_ids={"poi1"},
        nearby_building_ids={"b1"},
    )
    assert result.target is None


def test_valid_move_unchanged() -> None:
    """Valid move within bbox and max_move_m passes through unmodified."""
    s = _settings()
    d = Decision(action="move", target="poi1", destination={"lat": 35.6610, "lon": 139.7010})
    result = enforce_spatial_rules(
        settings=s,
        current_lat=35.6595,
        current_lon=139.7005,
        decision=d,
        nearby_poi_ids={"poi1"},
        nearby_building_ids=set(),
        max_move_m=300.0,
    )
    assert result.target == "poi1"
    assert abs(result.destination.lat - 35.6610) < 0.0001
