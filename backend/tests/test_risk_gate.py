import pytest

from parallelife.domain.decision import Decision
from parallelife.settings import Settings
from parallelife.usecases.risk_gate import enforce_spatial_rules


def test_reject_out_of_bbox() -> None:
    s = Settings(app_env="test")
    d = Decision(action="move", target="poi1", destination={"lat": 0.0, "lon": 0.0})
    with pytest.raises(ValueError, match="bounding box"):
        enforce_spatial_rules(
            settings=s,
            current_lat=35.6595,
            current_lon=139.7005,
            decision=d,
            nearby_poi_ids={"poi1"},
            nearby_building_ids=set(),
        )


def test_reject_too_far() -> None:
    s = Settings(app_env="test")
    d = Decision(action="move", target="poi1", destination={"lat": 35.6700, "lon": 139.7100})
    with pytest.raises(ValueError, match="Move distance"):
        enforce_spatial_rules(
            settings=s,
            current_lat=35.6595,
            current_lon=139.7005,
            decision=d,
            nearby_poi_ids={"poi1"},
            nearby_building_ids=set(),
        )


def test_reject_target_not_nearby() -> None:
    s = Settings(app_env="test")
    d = Decision(action="move", target="poi999", destination={"lat": 35.6595, "lon": 139.7005})
    with pytest.raises(ValueError, match="Target not in nearby"):
        enforce_spatial_rules(
            settings=s,
            current_lat=35.6595,
            current_lon=139.7005,
            decision=d,
            nearby_poi_ids={"poi1"},
            nearby_building_ids={"b1"},
        )
