class AdsLinkManager:
    def __init__(self, pool):
        self.pool = pool

    async def get_link(self):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT link FROM ads_link LIMIT 1")
            return row["link"] if row else None

    async def update_link(self, new_link: str):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE ads_link SET link=$1 WHERE id=1", new_link)
