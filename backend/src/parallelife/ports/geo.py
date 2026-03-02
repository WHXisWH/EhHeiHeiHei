from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class GeoRepository(ABC):
    @abstractmethod
    async def list_nearby_pois(self, *, lat: float, lon: float, radius_m: float) -> list[dict]: ...

    @abstractmethod
    async def list_nearby_buildings(self, *, lat: float, lon: float, radius_m: float) -> list[dict]: ...

    @abstractmethod
    async def get_poi(self, poi_id: str) -> dict | None: ...

    @abstractmethod
    async def get_building(self, building_id: str) -> dict | None: ...


class AgentLocator(ABC):
    @abstractmethod
    async def list_agents_within(self, *, lat: float, lon: float, radius_m: float) -> list[dict]: ...

