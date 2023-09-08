import json

from aiohttp import web
from sqlalchemy.exc import IntegrityError

from models import Ads, Base, Session, engine

app = web.Application()


def get_http_error(http_error_class, msg):
    return http_error_class(
        text=json.dumps({"error": msg}), content_type="application/json"
    )


async def orm_cntx(app: web.Application):
    print("START")
    async with engine.begin() as con:
        await con.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

    print("SHUT DOWN")


@web.middleware
async def session_middleware(request: web.Request, handler):
    async with Session() as session:
        request["session"] = session
        response = await handler(request)
        return response


app.cleanup_ctx.append(orm_cntx)
app.middlewares.append(session_middleware)


async def get_ads(ad_id: int, session: Session):
    ad = await session.get(Ads, ad_id)
    if ad is None:
        raise get_http_error(web.HTTPNotFound, "ad not found")
    return ad


class Ads_view(web.View):
    @property
    def session(self) -> Session:
        return self.request["session"]

    @property
    def ad_id(self):
        return int(self.request.match_info["ad_id"])

    async def get(self):
        ad = await get_ads(self.ad_id, self.session)
        return web.json_response(
            {
                "id": ad.id,
                "title": ad.title,
                "description": ad.description,
                "created_at": ad.created_at.isoformat(),
                "owner": ad.owner,
            }
        )

    async def post(self):
        json_data = await self.request.json()
        ad = Ads(**json_data)
        try:
            self.session.add(ad)
            await self.session.commit()
        except IntegrityError as err:
            raise get_http_error(web.HTTPConflict, "ad already exists")
        ad = await get_ads(ad.id, self.session)
        return web.json_response({"id": ad.id})

    async def patch(self):
        json_data = await self.request.json()
        ad = await get_ads(self.ad_id, self.session)
        for k, v in json_data.items():
            setattr(ad, k, v)
        try:
            self.session.add(ad)
            await self.session.commit()
        except IntegrityError as err:
            raise get_http_error(web.HTTPConflict, "ad already exists")
        ad = await get_ads(ad.id, self.session)
        return web.json_response({"id": ad.id})

    async def delete(self):
        ad = await get_ads(self.ad_id, self.session)
        await self.session.delete(ad)
        await self.session.commit()
        return web.json_response({"status": "deleted"})


app.add_routes(
    [
        web.get(r"/ads/{ad_id:\d+}/", Ads_view),
        web.post(r"/ads/", Ads_view),
        web.patch(r"/ads/{ad_id:\d+}/", Ads_view),
        web.delete(r"/ads/{ad_id:\d+}/", Ads_view),
    ]
)

if __name__ == "__main__":
    web.run_app(app)
