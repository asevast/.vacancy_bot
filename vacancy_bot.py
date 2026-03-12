import asyncio
import logging
import psycopg2
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import requests
import pandas as pd
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROK_API_KEY = os.getenv("GROK_API_KEY")
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", 5432),
    "database": os.getenv("DB_NAME", "vacancy_bot"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS")
}

HH_API = "https://api.hh.ru/vacancies"
SJ_API = "https://api.superjob.ru/2.0/vacancies/"
HEADERS = {"User-Agent": "VacancyBotPro/1.0"}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# PostgreSQL подключение
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
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, external_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_source_salary ON vacancies(source, salary);
        CREATE INDEX IF NOT EXISTS idx_parsed_at ON vacancies(parsed_at);
    ''')
    conn.commit()
    cur.close()
    conn.close()

class SearchForm(StatesGroup):
    waiting_profession = State()
    waiting_salary_from = State()
    waiting_salary_to = State()
    waiting_region = State()

# Регионы (HH ID : SJ ID)
AREAS = {
    "Москва": {"hh": 1, "sj": 4},
    "СПб": {"hh": 2, "sj": 2}, 
    "Нижний Новгород": {"hh": 56, "sj": 64},
    "Екатеринбург": {"hh": 2101, "sj": 3},
    "Казань": {"hh": 35, "sj": 25},
    "Все": {"hh": 113, "sj": None}
}

def parse_hh_vacancies(text, area=113, salary_from=None, salary_to=None, count=50):
    """HH.ru API"""
    params = {"text": text, "area": area, "per_page": min(count, 100)}
    if salary_from: params["salary_from"] = salary_from
    if salary_to: params["salary_to"] = salary_to
    
    try:
        resp = requests.get(HH_API, params=params, headers=HEADERS)
        data = resp.json()
        
        vacancies = []
        for vac in data["items"]:
            salary = vac.get("salary", {})
            salary_rub = salary.get("from", 0) if salary.get("currency") == "RUR" else 0
            
            skills = [s["name"] for s in vac.get("key_skills", [])]
            desc = vac.get("snippet", {}).get("requirement", "") + " " + vac.get("snippet", {}).get("responsibility", "")
            
            # Улучшенный парсинг зарплаты
            salary_rub = 0
            if salary:
                if salary.get("currency") == "RUR":
                    from_val = salary.get("from", 0)
                    to_val = salary.get("to", 0)
                    if from_val and to_val:
                        salary_rub = (from_val + to_val) // 2  # Среднее
                    elif from_val:
                        salary_rub = from_val
                    elif to_val:
                        salary_rub = to_val
                "source": "hh",
                "external_id": vac["id"],
                "name": vac["name"],
                "company": vac["employer"]["name"],
                "salary": salary_rub,
                "description": desc,
                "skills": skills,
                "experience": vac["experience"]["id"],
                "url": vac["alternate_url"]
            })
        return pd.DataFrame(vacancies)
    except:
        return pd.DataFrame()

def parse_superjob_vacancies(text, town_id=4, payment_from=None, payment_to=None, count=50):
    """SuperJob API (без авторизации)"""
    params = {
        "keyword": text,
        "town": town_id,  # Москва=4
        "count": min(count, 120),
        "order_field": "payment",
        "order_direction": "desc"
    }
    if payment_from: params["payment_from"] = payment_from
    if payment_to: params["payment_to"] = payment_to
    params["no_agreement"] = 1
    
    try:
        resp = requests.get(SJ_API, params=params, headers=HEADERS)
        data = resp.json()
        
        vacancies = []
        for vac in data.get("objects", []):
            salary_from = vac.get("payment_from", 0)
            salary_to = vac.get("payment_to", 0)
            salary_avg = 0
            if salary_from and salary_to:
                salary_avg = (salary_from + salary_to) // 2
            elif salary_from:
                salary_avg = salary_from
            elif salary_to:
                salary_avg = salary_to
            
            vacancies.append({
                "source": "sj",
                "external_id": str(vac["id"]),
                "name": vac["profession"],
                "company": vac.get("firm_name", "N/A"),
                "salary": salary_avg,
                "description": vac.get("candidat", ""),
                "skills": vac.get("professions", []),
                "experience": vac.get("experience", {}).get("id", "no_exp"),
                "url": f"https://www.superjob.ru/vakansii/{vac['id']}.html"
            })
        return pd.DataFrame(vacancies)
    except:
        return pd.DataFrame()

def cache_vacancies(df):
    """Сохранить в PostgreSQL"""
    if df.empty:
        return
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    for _, vac in df.iterrows():
        try:
            cur.execute('''
                INSERT INTO vacancies 
                (source, external_id, name, company, salary, description, skills, experience, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, external_id) DO NOTHING
            ''', (
                vac["source"], vac["external_id"], vac["name"], vac["company"],
                vac["salary"], vac["description"], vac["skills"], 
                vac["experience"], vac["url"]
            ))
        except Exception as e:
            logging.error(f"DB insert error: {e}")
    
    conn.commit()
    cur.close()
    conn.close()

def get_cached_vacancies(text, hours=24):
    """Вакансии из кэша"""
    conn = get_db_connection()
    query = """
        SELECT * FROM vacancies 
        WHERE name ILIKE %s OR description ILIKE %s
        AND parsed_at > NOW() - INTERVAL '%s hours'
        ORDER BY salary DESC LIMIT 100
    """
    df = pd.read_sql_query(query, conn, params=(f'%{text}%', f'%{text}%', hours))
    conn.close()
    return df if not df.empty else None

def cluster_vacancies(df):
    """ML кластеризация по сложности"""
    if len(df) < 5:
        return df.assign(cluster="mixed")
    
    # TF-IDF на описаниях + навыках
    text_data = df['description'].fillna('') + ' ' + df['skills'].astype(str)
    vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    X = vectorizer.fit_transform(text_data)
    
    # KMeans кластеризация (3 группы сложности)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)
    
    # Маппинг: 0=Junior, 1=Middle, 2=Senior (по средней зарплате)
    cluster_salaries = df.groupby(clusters)['salary'].mean()
    mapping = {cluster_salaries.idxmin(): "Junior",
               cluster_salaries.idxmax(): "Senior"}
    mapping[set([0,1,2]) - set(mapping.keys()).pop()] = "Middle"
    
    return df.assign(cluster=[mapping[c] for c in clusters])

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Анализ HH+SuperJob", callback_data="analyze")],
        [InlineKeyboardButton(text="🧠 AI Анализ", callback_data="ai_mode")],
        [InlineKeyboardButton(text="📊 Кластеры сложности", callback_data="clusters")]
    ])
    
    await message.answer(
        "🚀 *Vacancy Analyzer PRO*

"
        "✅ HH.ru + SuperJob
"
        "✅ PostgreSQL кэш (24ч)
"
        "✅ ML кластеризация
"
        "✅ AI анализ

"
        "_Нижний Новгород по умолчанию_",
        reply_markup=keyboard, parse_mode="Markdown"
    )

@dp.message(SearchForm.waiting_region)
async def process_region(message: types.Message, state: FSMContext):
    data = await state.get_data()
    region = message.text.title()
    area = AREAS.get(region, AREAS["Нижний Новгород"])
    
    await message.answer("🔍 *Ищу на HH.ru + SuperJob*
💾 Проверяю кэш...")
    
    # 1. Проверяем кэш
    cached = get_cached_vacancies(data["profession"])
    if cached is not None and len(cached) > 10:
        df = cached
        await message.answer(f"📦 Использую кэш ({len(df)} вакансий)")
    else:
        # 2. Парсим HH + SuperJob
        hh_df = parse_hh_vacancies(
            data["profession"], area["hh"],
            data.get("salary_from"), data.get("salary_to")
        )
        sj_df = parse_superjob_vacancies(
            data["profession"], area.get("sj"),
            data.get("salary_from"), data.get("salary_to")
        )
        
        df = pd.concat([hh_df, sj_df], ignore_index=True)
        cache_vacancies(df)  # Сохраняем
        
        await message.answer(f"✅ Найдено {len(df)} вакансий")
    
    # 3. ML кластеризация
    df_clustered = cluster_vacancies(df)
    
    # 4. Статистика
    salary_stats = df["salary"].describe()
    clusters_stats = df_clustered["cluster"].value_counts()
    
    stats_text = (
        f"📊 *{len(df)} вакансий*

"
        f"💰 Медиана: *{salary_stats['50%']:,.0f} ₽*
"
        f"📈 Диапазон: {salary_stats['min']:,.0f} - {salary_stats['max']:,.0f} ₽

"
        f"🎯 Кластеры сложности:
"
    )
    for cluster, count in clusters_stats.items():
        avg_salary = df_clustered[df_clustered["cluster"] == cluster]["salary"].mean()
        stats_text += f"• *{cluster}*: {count} ({avg_salary:,.0f} ₽)
"
    
    await message.answer(stats_text, parse_mode="Markdown")
    
    # Топ по кластерам
    for cluster in ["Senior", "Middle", "Junior"]:
        cluster_vacs = df_clustered[df_clustered["cluster"] == cluster].head(2)
        if not cluster_vacs.empty:
            text = f"🏆 *{cluster}* ({len(cluster_vacs)} вакансий)

"
            for _, vac in cluster_vacs.iterrows():
                text += f"*{vac['name']}*
`{vac['company']}` | {vac['salary']:,} ₽
"
                text += f"[ссылка]({vac['url']})

"
            await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
    
    await state.clear()

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())