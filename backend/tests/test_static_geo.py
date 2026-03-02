from pathlib import Path

import pytest

from parallelife.adapters.static_geo import StaticGeoRepository


@pytest.mark.asyncio
async def test_static_geo_nearby_sorted() -> None:
    repo = StaticGeoRepository(Path(__file__).resolve().parents[1] / "data" / "demo_geo.json")
    pois = await repo.list_nearby_pois(lat=35.6595, lon=139.7005, radius_m=300)
    assert pois
    assert pois[0]["distance"] <= pois[-1]["distance"]
