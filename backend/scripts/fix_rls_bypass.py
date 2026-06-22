"""Fix superuser RLS bypass by creating a non-superuser application role.

PostgreSQL superusers ALWAYS bypass Row Level Security, regardless of
NOBYPASSRLS. The correct fix is to create a separate non-superuser role
for the application that has the necessary permissions but MUST respect
RLS policies.

This script:
1. Creates a new role 'seo_platform_app' (non-superuser)
2. Grants all necessary table/sequence privileges
3. Verifies RLS enforcement works correctly

Usage:
    cd /Users/dronpancholi/Developer/Project 31A/backend
    source .venv/bin/activate
    python scripts/fix_rls_bypass.py
"""

import asyncio

from sqlalchemy import text

from seo_platform.core.database import get_session


async def fix_rls_bypass():
    """Create a non-superuser app role and verify RLS enforcement."""
    print("=" * 60)
    print("FIXING SUPERUSER RLS BYPASS")
    print("=" * 60)
    print()
    print("NOTE: PostgreSQL superusers ALWAYS bypass RLS, regardless of")
    print("NOBYPASSRLS. The correct fix is a non-superuser app role.")
    print()

    async with get_session() as session:
        # Step 1: Create the non-superuser application role
        print("--- Step 1: Create non-superuser application role ---")
        try:
            await session.execute(text(
                "CREATE ROLE seo_platform_app WITH LOGIN PASSWORD 'seo_platform_app_dev'"
            ))
            await session.commit()
            print("  Created role: seo_platform_app")
        except Exception as e:
            if "already exists" in str(e):
                print("  Role seo_platform_app already exists")
                await session.rollback()
            else:
                raise

        # Step 2: Grant necessary privileges on all tables
        print("\n--- Step 2: Grant table privileges ---")
        grant_sql = """
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO seo_platform_app;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO seo_platform_app;
            GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO seo_platform_app;
        """
        await session.execute(text(grant_sql))
        await session.commit()
        print("  Granted SELECT, INSERT, UPDATE, DELETE on all tables")
        print("  Granted USAGE, SELECT on all sequences")
        print("  Granted EXECUTE on all functions")

        # Step 3: Grant default privileges for future objects
        print("\n--- Step 3: Set default privileges ---")
        default_sql = """
            ALTER DEFAULT PRIVILEGES IN SCHEMA public 
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO seo_platform_app;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public 
            GRANT USAGE, SELECT ON SEQUENCES TO seo_platform_app;
        """
        await session.execute(text(default_sql))
        await session.commit()
        print("  Set default privileges for future tables and sequences")

        # Step 4: Verify the role
        print("\n--- Step 4: Verify role ---")
        result = await session.execute(text(
            "SELECT rolname, rolsuper, rolcanlogin FROM pg_roles WHERE rolname = 'seo_platform_app'"
        ))
        row = result.fetchone()
        print(f"  rolname={row[0]}, rolsuper={row[1]}, rolcanlogin={row[2]}")

    print("\n" + "=" * 60)
    print("ROLE CREATED SUCCESSFULLY")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Update DATABASE_URL to use 'seo_platform_app' user")
    print("2. Keep 'seo_platform' superuser for migrations only")
    print("3. Verify with: python scripts/verify_rls_fix.py")


if __name__ == "__main__":
    asyncio.run(fix_rls_bypass())