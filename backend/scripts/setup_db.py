"""One-time script to create the billwise role and database in local PostgreSQL."""

import asyncio
import asyncpg


async def setup() -> None:
    # Connect to the default PostgreSQL administrative database as superuser
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/template1")
    try:
        # 1. Check and create the 'billwise' role (user)
        role_exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'billwise'")
        if not role_exists:
            await conn.execute("CREATE ROLE billwise WITH LOGIN PASSWORD 'billwise' SUPERUSER CREATEDB")
            print("✅ Role 'billwise' created successfully.")
        else:
            print("ℹ️ Role 'billwise' already exists.")

        # 2. Check and create the 'billwise' database
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'billwise'")
        if not db_exists:
            await conn.execute("CREATE DATABASE billwise OWNER billwise")
            print("✅ Database 'billwise' created successfully.")
        else:
            print("ℹ️ Database 'billwise' already exists.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(setup())