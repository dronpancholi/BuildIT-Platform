import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect("postgresql://seo_platform:seo_platform_dev@localhost:5432/seo_platform")
    try:
        rows = await conn.fetch("SELECT id, tenant_id, client_id, business_name, website_url, status FROM citation_projects")
        print("Citation Projects:")
        for r in rows:
            print(f"  * ID: {r['id']}, Tenant: {r['tenant_id']}, Client: {r['client_id']}, Business: {r['business_name']}, Web: {r['website_url']}, Status: {r['status']}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
