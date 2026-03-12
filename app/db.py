import psycopg2
import pandas as pd
import sys

from app.config import DB_CONFIG, logger


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vacancies (
            id SERIAL PRIMARY KEY,
            source VARCHAR(10),
            external_id VARCHAR(50),
            name TEXT,
            company TEXT,
            salary INTEGER,
            description TEXT,
            skills TEXT[],
            experience VARCHAR(20),
            url TEXT,
            region TEXT,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, external_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_source_salary ON vacancies(source, salary);
        CREATE INDEX IF NOT EXISTS idx_parsed_at ON vacancies(parsed_at);
    ''')
    cur.execute("ALTER TABLE vacancies ADD COLUMN IF NOT EXISTS region TEXT;")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_region ON vacancies(region);")

    cur.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            profession TEXT NOT NULL,
            region TEXT,
            salary_from INTEGER,
            salary_to INTEGER,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sent_at TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(active);
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id BIGINT PRIMARY KEY,
            region TEXT,
            salary_from INTEGER,
            salary_to INTEGER,
            level TEXT,
            work_format TEXT,
            technologies TEXT[],
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()


def cache_vacancies(df):
    """Save to PostgreSQL"""
    if df.empty:
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    for _, vac in df.iterrows():
        try:
            skills = vac["skills"] if isinstance(vac["skills"], list) else str(vac["skills"])
            
            cur.execute('''
                INSERT INTO vacancies 
                (source, external_id, name, company, salary, description, skills, experience, url, region)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, external_id) DO NOTHING
            ''', (
                vac["source"], vac["external_id"], vac["name"], vac["company"],
                vac["salary"], vac["description"], skills, 
                vac["experience"], vac["url"], vac.get("region")
            ))
        except Exception as e:
            logger.error(f"DB insert error: {e}")
    
    conn.commit()
    cur.close()
    conn.close()


def safe_cache_vacancies(df):
    """Cache vacancies without interrupting the search flow on errors."""
    try:
        mod = sys.modules.get("vacancy_bot")
        if mod and hasattr(mod, "cache_vacancies"):
            mod.cache_vacancies(df)
        else:
            cache_vacancies(df)
    except Exception as e:
        logger.error(f"CACHE SAVE ERROR | {e}")


def get_cached_vacancies(text, hours=24, region=None, salary_from=None, salary_to=None):
    """Get vacancies from cache"""
    try:
        conn = get_db_connection()
        conditions = [
            "(name ILIKE %s OR description ILIKE %s)",
            "parsed_at > NOW() - (INTERVAL '1 hour' * %s)"
        ]
        params = [f'%{text}%', f'%{text}%', hours]

        if region and region != "Все":
            conditions.append("region = %s")
            params.append(region)
        if salary_from is not None:
            conditions.append("salary >= %s")
            params.append(salary_from)
        if salary_to is not None:
            conditions.append("salary <= %s")
            params.append(salary_to)

        query = f"""
            SELECT * FROM vacancies 
            WHERE {' AND '.join(conditions)}
            ORDER BY salary DESC LIMIT 100
        """
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df if not df.empty else None
    except Exception as e:
        logger.error(f"CACHE READ ERROR | {e}")
        return None


def get_cached_vacancies_since(text, since_dt, region=None, salary_from=None, salary_to=None):
    """Get vacancies from cache since specific datetime"""
    try:
        conn = get_db_connection()
        conditions = [
            "(name ILIKE %s OR description ILIKE %s)",
            "parsed_at > %s"
        ]
        params = [f'%{text}%', f'%{text}%', since_dt]

        if region and region != "Все":
            conditions.append("region = %s")
            params.append(region)
        if salary_from is not None:
            conditions.append("salary >= %s")
            params.append(salary_from)
        if salary_to is not None:
            conditions.append("salary <= %s")
            params.append(salary_to)

        query = f"""
            SELECT * FROM vacancies 
            WHERE {' AND '.join(conditions)}
            ORDER BY salary DESC LIMIT 100
        """
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df if not df.empty else None
    except Exception as e:
        logger.error(f"CACHE READ ERROR | {e}")
        return None


def add_subscription(user_id, profession, region=None, salary_from=None, salary_to=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        INSERT INTO subscriptions (user_id, profession, region, salary_from, salary_to)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        ''',
        (user_id, profession, region, salary_from, salary_to)
    )
    sub_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return sub_id


def list_subscriptions(user_id):
    conn = get_db_connection()
    df = pd.read_sql_query(
        '''
        SELECT id, profession, region, salary_from, salary_to, active, created_at, last_sent_at
        FROM subscriptions
        WHERE user_id = %s
        ORDER BY created_at DESC
        ''',
        conn,
        params=(user_id,)
    )
    conn.close()
    return df


def deactivate_subscription(user_id, sub_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'UPDATE subscriptions SET active = FALSE WHERE user_id = %s AND id = %s',
        (user_id, sub_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def update_subscription_last_sent(sub_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'UPDATE subscriptions SET last_sent_at = NOW() WHERE id = %s',
        (sub_id,)
    )
    conn.commit()
    cur.close()
    conn.close()
