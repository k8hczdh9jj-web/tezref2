# database.py
import asyncpg 
from config import DATABASE_URL, ssl_context 

db_pool = None

async def get_db_pool():
    global db_pool
    if db_pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set.")
        db_pool = await asyncpg.create_pool(DATABASE_URL, ssl=ssl_context)
    return db_pool

async def init_db(pool):
    async with pool.acquire() as conn:
        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                phone_number TEXT,
                created_at TIMESTAMP DEFAULT now(),
                balance BIGINT DEFAULT 0,
                referrals INTEGER DEFAULT 0,
                weekly_refs INTEGER DEFAULT 0,
                level TEXT DEFAULT 'Oddiy',
                ref_code TEXT UNIQUE,
                invited_by BIGINT,
                blocked INTEGER DEFAULT 0,
                pending_withdraw BOOLEAN DEFAULT FALSE
            )
        """)

        # Eski bazalarda phone_number bo'lmasa, qo'shib qo'yamiz
        await conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS phone_number TEXT
        """)
        await conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()
        """)
        await conn.execute("""
            UPDATE users
            SET created_at = now()
            WHERE created_at IS NULL
        """)
        await conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS group_added_count INTEGER DEFAULT 0
        """)
        await conn.execute("""
            UPDATE users
            SET group_added_count = 0
            WHERE group_added_count IS NULL
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS group_invite_credits (
                invited_user_id BIGINT PRIMARY KEY,
                first_inviter_user_id BIGINT NOT NULL,
                group_id BIGINT NOT NULL,
                bonus_amount BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_bonus_claims (
                user_id BIGINT NOT NULL,
                claim_date DATE NOT NULL,
                amount BIGINT NOT NULL,
                streak_day INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT now(),
                PRIMARY KEY (user_id, claim_date)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bonus_config (
                id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                referral_bonus_delta INTEGER NOT NULL DEFAULT 0,
                group_bonus_delta INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT now()
            )
        """)

        await conn.execute("""
            INSERT INTO bonus_config (id, referral_bonus_delta, group_bonus_delta)
            VALUES (1, 0, 0)
            ON CONFLICT (id) DO NOTHING
        """)

        # Team bo'limi olib tashlangani uchun eski team obyektlarini o'chiramiz
        await conn.execute("""
            ALTER TABLE users DROP COLUMN IF EXISTS team_id
        """)
        await conn.execute("""
            ALTER TABLE users DROP COLUMN IF EXISTS left_team_at
        """)
        await conn.execute("""
            ALTER TABLE users DROP COLUMN IF EXISTS total_team_contribution
        """)
        await conn.execute("""
            DROP TABLE IF EXISTS team_requests CASCADE
        """)
        await conn.execute("""
            DROP TABLE IF EXISTS team_transactions CASCADE
        """)
        await conn.execute("""
            DROP TABLE IF EXISTS team_members CASCADE
        """)
        await conn.execute("""
            DROP TABLE IF EXISTS teams CASCADE
        """)

        # Promo tables (O'zgarishsiz)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                amount BIGINT NOT NULL,
                max_uses INT NOT NULL,
                uses_left INT NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                channel_id BIGINT DEFAULT NULL,
                created_by BIGINT,
                created_at TIMESTAMP DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS promo_claims (
                code TEXT REFERENCES promo_codes(code),
                user_id BIGINT,
                claimed_at TIMESTAMP DEFAULT now(),
                PRIMARY KEY (code, user_id)
            )
        """)

        # Reklama linki uchun jadval
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ads_link (
                id SERIAL PRIMARY KEY,
                link TEXT NOT NULL
            );
        """)

        # Agar jadval bo‘sh bo‘lsa — default link qo‘shib qo‘yamiz
        await conn.execute("""
            INSERT INTO ads_link (link)
            SELECT 'https://t.me/default_group'
            WHERE NOT EXISTS (SELECT 1 FROM ads_link);
        """)

        print("Database initialized successfully 🔌")