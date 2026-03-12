import asyncio
import logging
import sys
from datetime import datetime
import psycopg2
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.middleware.types import MessageMiddlewareAnnotation
import requests
from requests.exceptions import RequestException, Timeout
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import os
from dotenv import load_dotenv

# Настройка логирования в терминал
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

load_dotenv()

# Настройки из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROK_API_KEY = os.getenv("GROK_API_KEY")
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "vacancy_bot"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS")
}

HH_API = "https://api.hh.ru/vacancies"
SJ_API = "https://api.superjob.ru/2.0/vacancies/"
HEADERS = {"User-Agent": "VacancyBotPro/1.0"}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Простой декоратор для логирования сообщений
def log_message(func):
    async def wrapper(message: types.Message):
        user = message.from_user
        text = message.text[:50] if message.text else "non-text"
        logger.info(f"📩 MSG | {user.full_name} (@{user.username or 'N/A'}) | {text}")
        return await func(message)
    return wrapper

# Простой декоратор для логирования callback
def log_callback(func):
    async def wrapper(callback: types.CallbackQuery):
        user = callback.from_user
        logger.info(f"📲 CALLBACK | {user.full_name} (@{user.username or 'N/A'}) | {callback.data}")
        return await func(callback)
    return wrapper

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
    logger.info(f"→ HH.ru API request: text='{text}', area={area}")
    
    params = {"text": text, "area": area, "per_page": min(count, 100)}
    if salary_from: params["salary_from"] = salary_from
    if salary_to: params["salary_to"] = salary_to
    
    try:
        resp = requests.get(HH_API, params=params, headers=HEADERS, timeout=30)
        data = resp.json()
        
        vacancies = []
        for vac in data["items"]:
            salary = vac.get("salary")
            salary_rub = 0
            
            # Улучшенный парсинг зарплаты
            if salary:
                if salary.get("currency") == "RUR":
                    from_val = salary.get("from")
                    to_val = salary.get("to")
                    if from_val and to_val:
                        salary_rub = (from_val + to_val) // 2
                    elif from_val:
                        salary_rub = from_val
                    elif to_val:
                        salary_rub = to_val
            
            skills = [s["name"] for s in vac.get("key_skills", [])]
            desc = vac.get("snippet", {}).get("requirement", "") + " " + vac.get("snippet", {}).get("responsibility", "")
            
            vacancies.append({
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
    except Timeout:
        logger.error(f"❌ HH.ru TIMEOUT | text='{text}'")
        raise TimeoutError("Превышен таймаут при запросе к HH.ru. Попробуйте позже.")
    except RequestException as e:
        logger.error(f"❌ HH.ru ERROR | {e}")
        raise ConnectionError(f"Ошибка соединения с HH.ru: {e}")
    except Exception as e:
        logger.error(f"❌ HH.ru UNEXPECTED | {e}")
        raise

def parse_superjob_vacancies(text, town_id=4, payment_from=None, payment_to=None, count=50):
    """SuperJob API (без авторизации)"""
    logger.info(f"→ SuperJob API request: text='{text}', town_id={town_id}")
    
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
        resp = requests.get(SJ_API, params=params, headers=HEADERS, timeout=30)
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
    except Timeout:
        logger.error(f"❌ SuperJob TIMEOUT | text='{text}'")
        raise TimeoutError("Превышен таймаут при запросе к SuperJob. Попробуйте позже.")
    except RequestException as e:
        logger.error(f"❌ SuperJob ERROR | {e}")
        raise ConnectionError(f"Ошибка соединения с SuperJob: {e}")
    except Exception as e:
        logger.error(f"❌ SuperJob UNEXPECTED | {e}")
        raise

def cache_vacancies(df):
    """Сохранить в PostgreSQL"""
    if df.empty:
        return
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    for _, vac in df.iterrows():
        try:
            # Исправлено: преобразуем skills в массив PostgreSQL
            skills = vac["skills"] if isinstance(vac["skills"], list) else str(vac["skills"])
            
            cur.execute('''
                INSERT INTO vacancies 
                (source, external_id, name, company, salary, description, skills, experience, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, external_id) DO NOTHING
            ''', (
                vac["source"], vac["external_id"], vac["name"], vac["company"],
                vac["salary"], vac["description"], skills, 
                vac["experience"], vac["url"]
            ))
        except Exception as e:
            logging.error(f"DB insert error: {e}")
    
    conn.commit()
    cur.close()
    conn.close()

def get_cached_vacancies(text, hours=24):
    """Вакансии из кэша"""
    try:
        conn = get_db_connection()
        conn.timeout = 10  # таймаут 10 секунд
        query = """
            SELECT * FROM vacancies 
            WHERE (name ILIKE %s OR description ILIKE %s)
            AND parsed_at > NOW() - (INTERVAL '1 hour' * %s)
            ORDER BY salary DESC LIMIT 100
        """
        # Исправлено: параметры передаются кортежем
        df = pd.read_sql_query(query, conn, params=(f'%{text}%', f'%{text}%', hours))
        conn.close()
        return df if not df.empty else None
    except Exception as e:
        logger.error(f"❌ CACHE READ ERROR | {e}")
        return None

def cluster_vacancies(df):
    """ML кластеризация по сложности"""
    if len(df) < 5:
        return df.assign(cluster="mixed")
    
    # Проверяем наличие зарплат
    if 'salary' not in df.columns or df['salary'].isna().all():
        return df.assign(cluster="unknown")
    
    # Фильтруем строки с зарплатой для маппинга
    df = df.copy()
    df['description'] = df['description'].fillna('')
    df['skills'] = df['skills'].apply(lambda x: ' '.join(x) if isinstance(x, list) else str(x))
    
    text_data = df['description'] + ' ' + df['skills'].astype(str)
    vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    X = vectorizer.fit_transform(text_data)
    
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)
    
    # Правильный маппинг по зарплате
    df_temp = df.copy()
    df_temp['cluster_num'] = clusters
    cluster_salaries = df_temp.groupby('cluster_num')['salary'].mean().sort_values()
    cluster_ids = list(cluster_salaries.index)
    
    mapping = {
        cluster_ids[0]: "Junior",
        cluster_ids[1]: "Middle", 
        cluster_ids[2]: "Senior"
    }
    
    return df.assign(cluster=[mapping.get(c, "Middle") for c in clusters])

# Обработчики FSM

@dp.message(SearchForm.waiting_profession)
@log_message
async def process_profession(message: types.Message, state: FSMContext):
    await state.update_data(profession=message.text)
    await message.answer("Введите минимальную зарплату (или /skip):")
    await state.set_state(SearchForm.waiting_salary_from)


@dp.message(SearchForm.waiting_salary_from)
@log_message
async def process_salary_from(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_from=int(salary))
    await message.answer("Введите максимальную зарплату (или /skip):")
    await state.set_state(SearchForm.waiting_salary_to)


@dp.message(SearchForm.waiting_salary_to)
@log_message
async def process_salary_to(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_to=int(salary))
    await message.answer("Введите регион (Москва, СПб, Нижний Новгород, Казань, Екатеринбург):")
    await state.set_state(SearchForm.waiting_region)


# Callback обработчики

@dp.callback_query(F.data == "analyze")
@log_callback
async def analyze_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название профессии:")
    await state.set_state(SearchForm.waiting_profession)
    await callback.answer()


@dp.callback_query(F.data == "ai_mode")
@log_callback
async def ai_mode_callback(callback: types.CallbackQuery):
    await callback.message.answer("🧠 AI анализ временно недоступен. Требуется GROK_API_KEY в .env")
    await callback.answer()


@dp.callback_query(F.data == "clusters")
@log_callback
async def clusters_callback(callback: types.CallbackQuery):
    await callback.message.answer("📊 Для просмотра кластеров выполните поиск: /search Python")
    await callback.answer()


@dp.message(Command("start"))
@log_message
async def start_handler(message: types.Message):
    logger.info(f"🟢 START command | {message.from_user.full_name}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Анализ HH+SuperJob", callback_data="analyze")],
        [InlineKeyboardButton(text="🧠 AI Анализ", callback_data="ai_mode")],
        [InlineKeyboardButton(text="📊 Кластеры сложности", callback_data="clusters")]
    ])
    
    await message.answer(
        "🚀 *Vacancy Analyzer PRO*\n"
        "✅ HH.ru + SuperJob\n"
        "✅ PostgreSQL кэш (24ч)\n"
        "✅ ML кластеризация\n"
        "✅ AI анализ\n"
        "_Нижний Новгород по умолчанию_",
        reply_markup=keyboard, parse_mode="Markdown"
    )

@dp.message(SearchForm.waiting_region)
@log_message
async def process_region(message: types.Message, state: FSMContext):
    data = await state.get_data()
    region = message.text.title()
    area = AREAS.get(region, AREAS["Нижний Новгород"])
    
    await state.update_data(area=area, region=region)
    await message.answer("🔍 Ищу на HH.ru + SuperJob...")
    
    # Выполняем поиск
    profession = data.get("profession", "")
    salary_from = data.get("salary_from")
    salary_to = data.get("salary_to")
    
    logger.info(f"🔍 SEARCH | profession: '{profession}' | region: {region} | salary: {salary_from}-{salary_to}")
    
    try:
        # Проверяем кэш
        cached = get_cached_vacancies(profession)
        
        if cached is not None and not cached.empty:
            df = cached
            logger.info(f"💾 CACHE HIT | '{profession}' | {len(df)} vacancies")
        else:
            # Парсим с HH и SuperJob
            logger.info(f"🌐 PARSING HH.ru | profession: '{profession}'")
            hh_df = parse_hh_vacancies(profession, area=area.get("hh"), salary_from=salary_from, salary_to=salary_to)
            logger.info(f"🌐 PARSING SuperJob | profession: '{profession}'")
            sj_df = parse_superjob_vacancies(profession, town_id=area.get("sj", 4), payment_from=salary_from, payment_to=salary_to)
            
            df = pd.concat([hh_df, sj_df], ignore_index=True)
            
            if not df.empty:
                cache_vacancies(df)
                logger.info(f"💾 CACHE SAVED | {len(df)} vacancies")
        
        if df.empty:
            await message.answer("Вакансии не найдены")
        else:
            # Кластеризация
            df = cluster_vacancies(df)
            
            # Формируем ответ
            result = f"📋 Найдено: {len(df)} вакансий\n\n"
            for level in ["Junior", "Middle", "Senior", "mixed", "unknown"]:
                level_df = df[df['cluster'] == level]
                if not level_df.empty:
                    result += f"<b>{level}</b>: {len(level_df)} вакансий\n"
            
            await message.answer(result)
            
            # Показываем первые результаты
            for _, vac in df.head(5).iterrows():
                await message.answer(
                    f"🔹 {vac['name']}\n"
                    f"💰 {vac.get('salary', 'N/A')}₽\n"
                    f"🏢 {vac.get('company', 'N/A')}\n"
                    f"📍 {vac.get('source', '?')}"
                )
                
    except TimeoutError as e:
        logger.error(f"❌ TIMEOUT | {e}")
        await message.answer("⏱️ Превышен таймаут ожидания от сервера. Попробуйте ещё раз или повторите запрос позже.")
    except ConnectionError as e:
        logger.error(f"❌ CONNECTION ERROR | {e}")
        await message.answer("🔌 Не удалось подключиться к серверу вакансий. Проверьте интернет-соединение и попробуйте позже.")
    except Exception as e:
        logger.error(f"❌ SEARCH ERROR | {e}")
        await message.answer(f"⚠️ Произошла ошибка при поиске: {str(e)[:100]}")
    
    # Завершаем состояние
    await state.clear()
    await state.set_state(None)

async def main():
    logger.info("🚀 Starting Vacancy Analyzer PRO...")
    logger.info(f"📡 Bot token: {BOT_TOKEN[:15]}...")
    logger.info(f"🗄 DB: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    
    # Инициализация БД
    try:
        init_db()
        logger.info("✅ Database connected and initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
    
    logger.info("🤖 Bot is polling for updates...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())