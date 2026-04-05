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
        # Teams avval yaratiladi, chunki users.team_id -> teams(team_id) FK bor
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id SERIAL PRIMARY KEY,
                team_name TEXT UNIQUE NOT NULL,
                creator_id BIGINT UNIQUE NOT NULL,
                creator_username TEXT,
                invite_link TEXT UNIQUE,
                members_count INT DEFAULT 1,
                team_coins INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT now()
            )
        """)

        # Users table (YANGILANGAN: total_team_contribution ustuni qo'shildi)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                phone_number TEXT,
                balance BIGINT DEFAULT 0,
                referrals INTEGER DEFAULT 0,
                weekly_refs INTEGER DEFAULT 0,
                level TEXT DEFAULT 'Oddiy',
                ref_code TEXT UNIQUE,
                invited_by BIGINT,
                blocked INTEGER DEFAULT 0,
                pending_withdraw BOOLEAN DEFAULT FALSE,
                team_id INT REFERENCES teams(team_id),
                left_team_at TIMESTAMP DEFAULT NULL,
                -- YANGI: Jamoaga qo'shilgan umumiy tanga miqdori
                total_team_contribution BIGINT DEFAULT 0
            )
        """)

        # Eski bazalarda phone_number bo'lmasa, qo'shib qo'yamiz
        await conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS phone_number TEXT
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

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                team_id INT REFERENCES teams(team_id) ON DELETE CASCADE,
                user_id BIGINT UNIQUE,
                joined_at TIMESTAMP DEFAULT now(),
                PRIMARY KEY(team_id, user_id)
            )
        """)
        
        # YANGI: Team Tranzaksiyalarni Loglash Jadvali (Admin nazorati uchun)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS team_transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                team_id INT REFERENCES teams(team_id) ON DELETE CASCADE,
                amount_money INTEGER NOT NULL,
                amount_coins INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS team_requests (
                request_id SERIAL PRIMARY KEY,  -- << VERGUL QO'SHILDI
                team_id INTEGER REFERENCES teams(team_id),
                username VARCHAR(255),
                user_id BIGINT UNIQUE NOT NULL,
                leader_id BIGINT NOT NULL,
                request_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE (team_id, user_id)
            );
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