import re
import pandas as pd

from app.config import logger
from app.db import get_db_connection
from app.utils import normalize_region_input


def init_profile_table():
    conn = get_db_connection()
    cur = conn.cursor()
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


def get_user_profile(user_id):
    conn = get_db_connection()
    df = pd.read_sql_query(
        '''
        SELECT user_id, region, salary_from, salary_to, level, work_format, technologies, updated_at
        FROM user_profiles
        WHERE user_id = %s
        ''',
        conn,
        params=(user_id,)
    )
    conn.close()
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def upsert_user_profile(user_id, region=None, salary_from=None, salary_to=None, level=None, work_format=None, technologies=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        INSERT INTO user_profiles (user_id, region, salary_from, salary_to, level, work_format, technologies, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            region = EXCLUDED.region,
            salary_from = EXCLUDED.salary_from,
            salary_to = EXCLUDED.salary_to,
            level = EXCLUDED.level,
            work_format = EXCLUDED.work_format,
            technologies = EXCLUDED.technologies,
            updated_at = NOW()
        ''',
        (user_id, region, salary_from, salary_to, level, work_format, technologies)
    )
    conn.commit()
    cur.close()
    conn.close()


def normalize_level(raw):
    if not raw:
        return None
    val = raw.strip().lower()
    mapping = {
        "junior": "junior",
        "middle": "middle",
        "senior": "senior",
        "lead": "lead",
        "jun": "junior",
        "mid": "middle",
        "sr": "senior",
        "джун": "junior",
        "мидл": "middle",
        "сеньор": "senior",
        "лид": "lead"
    }
    return mapping.get(val, raw.strip())


def normalize_format(raw):
    if not raw:
        return None
    val = raw.strip().lower()
    mapping = {
        "remote": "remote",
        "hybrid": "hybrid",
        "office": "office",
        "onsite": "office",
        "удаленно": "remote",
        "удалённо": "remote",
        "гибрид": "hybrid",
        "офис": "office"
    }
    return mapping.get(val, raw.strip())


def parse_technologies(text):
    if not text:
        return []
    parts = re.split(r"[,\n;]+", text)
    items = [p.strip() for p in parts if p.strip()]
    return items


def build_profile_defaults(profile):
    if not profile:
        return {}
    return {
        "region": profile.get("region"),
        "salary_from": profile.get("salary_from"),
        "salary_to": profile.get("salary_to"),
        "level": profile.get("level"),
        "work_format": profile.get("work_format"),
        "technologies": profile.get("technologies") or []
    }


def profile_summary(profile):
    if not profile:
        return "Профиль не заполнен."
    return (
        "Ваш профиль:\n"
        f"Регион: {profile.get('region') or '-'}\n"
        f"Зарплата: {profile.get('salary_from') or '-'}-{profile.get('salary_to') or '-'}\n"
        f"Уровень: {profile.get('level') or '-'}\n"
        f"Формат: {profile.get('work_format') or '-'}\n"
        f"Технологии: {', '.join(profile.get('technologies') or []) or '-'}"
    )
