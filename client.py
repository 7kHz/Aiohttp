import asyncio

import aiohttp


async def main():
    async with aiohttp.ClientSession() as session:
        response = await session.post(
            "http://127.0.0.1:8080/ads/",
            json={
                "title": "Ferrari",
                "description": "Best car in the world",
                "owner": "Enzo Ferrari",
            },
        )
        data = await response.text()
        print(data)


asyncio.run(main())
