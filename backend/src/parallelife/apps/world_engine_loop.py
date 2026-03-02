from __future__ import annotations

import asyncio
import os

import httpx


async def main() -> None:
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    interval_s = int(os.getenv("TICK_INTERVAL_SECONDS", "60"))

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                await client.post(f"{api_base}/internal/tick")
            except Exception as e:
                print(f"[world_engine_loop] tick failed: {e}")
            await asyncio.sleep(interval_s)


if __name__ == "__main__":
    asyncio.run(main())

