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
import aiohttp
import requests
from requests.exceptions import RequestException, Timeout
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import os
from dotenv import load_dotenv

# Настройка логирования в терминал (без эмодзи для совместимости с Windows)
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
KILO_AUTO_API_KEY = os.getenv("KILO_AUTO_API_KEY")
KILO_AUTO_API_URL = os.getenv("KILO_AUTO_API_URL")
KILO_AUTO_MODEL = os.getenv("KILO_AUTO_MODEL", "kilo-auto")

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

# Логирование (встроено вручную в каждый обработчик)

# Простой декоратор для логирования callback
def log_callback(func):
    async def wrapper(callback: types.CallbackQuery, state: FSMContext = None):
        user = callback.from_user
        logger.info(f"CALLBACK | {user.full_name} (@{user.username or 'N/A'}) | {callback.data}")
        if state:
            return await func(callback, state)
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

class AIForm(StatesGroup):
    waiting_prompt = State()

# Kilo Auto AI функция
async def ask_kilo_auto(prompt: str) -> str:
    """Отправка запроса к Kilo Auto AI"""
    if not KILO_AUTO_API_KEY:
        return "ERROR: KILO_AUTO_API_KEY not configured"
    
    # Use default URL if not provided
    url = KILO_AUTO_API_URL or "https://kilocode.ai/api/openrouter/chat/completions"
    headers = {
        "Authorization": f"Bearer {KILO_AUTO_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": KILO_AUTO_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await resp.text()
                    logger.error(f"Kilo Auto API error: {resp.status} - {error_text}")
                    return f"API ERROR: {resp.status}"
    except asyncio.TimeoutError:
        return "TIMEOUT: Kilo Auto request timeout"
    except Exception as e:
        logger.error(f"Kilo Auto request error: {e}")
        return f"ERROR: {str(e)}"


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
    logger.info(f"HH.ru API request: text='{text}', area={area}")
    
    params = {"text": text, "area": area, "per_page": min(count, 100)}
    if salary_from: params["salary_from"] = salary_from
    if salary_to: params["salary_to"] = salary_to
    
    try:
        resp = requests.get(HH_API, params=params, headers=HEADERS, timeout=30)
        data = resp.json()
        
        if "items" not in data:
            logger.warning(f"HH.ru response missing 'items': {data.get('errors', 'Unknown error')}")
            return pd.DataFrame()
        
        vacancies = []
        for vac in data.get("items", []):
            salary = vac.get("salary")
            salary_rub = 0
            
            # Improved salary parsing
            if salary and isinstance(salary, dict):
                currency = salary.get("currency")
                if currency == "RUR":
                    from_val = salary.get("from")
                    to_val = salary.get("to")
                    if from_val and to_val:
                        salary_rub = (from_val + to_val) // 2
                    elif from_val:
                        salary_rub = from_val
                    elif to_val:
                        salary_rub = to_val
            
            # Safe string concatenation
            snippet_req = vac.get("snippet", {}).get("requirement") or ""
            snippet_resp = vac.get("snippet", {}).get("responsibility") or ""
            desc = str(snippet_req) + " " + str(snippet_resp)
            
            skills = [s["name"] for s in vac.get("key_skills", [])]
            desc = vac.get("snippet", {}).get("requirement", "") + " " + vac.get("snippet", {}).get("responsibility", "")
            
            # Safe employer name extraction
            employer = vac.get("employer")
            company = employer.get("name") if employer else "Unknown"
            
            # Safe experience extraction
            experience = "unknown"
            exp_data = vac.get("experience")
            if exp_data and isinstance(exp_data, dict):
                experience = exp_data.get("id", "unknown")
            
            vacancies.append({
                "source": "hh",
                "external_id": vac["id"],
                "name": vac["name"],
                "company": company,
                "salary": salary_rub,
                "description": desc,
                "skills": skills,
                "experience": experience,
                "url": vac["alternate_url"]
            })
        return pd.DataFrame(vacancies)
    except Timeout:
        logger.error(f"HH.ru TIMEOUT | text='{text}'")
        raise TimeoutError("Timeout when requesting HH.ru. Try again later.")
    except RequestException as e:
        logger.error(f"HH.ru ERROR | {e}")
        raise ConnectionError(f"Connection error with HH.ru: {e}")
    except Exception as e:
        logger.error(f"HH.ru UNEXPECTED | {e}")
        raise

def parse_superjob_vacancies(text, town_id=4, payment_from=None, payment_to=None, count=50):
    """SuperJob API (без авторизации)"""
    logger.info(f"SuperJob API request: text='{text}', town_id={town_id}")
    
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
        logger.error(f"SuperJob TIMEOUT | text='{text}'")
        raise TimeoutError("Timeout when requesting SuperJob. Try again later.")
    except RequestException as e:
        logger.error(f"SuperJob ERROR | {e}")
        raise ConnectionError(f"Connection error with SuperJob: {e}")
    except Exception as e:
        logger.error(f"SuperJob UNEXPECTED | {e}")
        raise

def cache_vacancies(df):
    """Save to PostgreSQL"""
    if df.empty:
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    for _, vac in df.iterrows():
        try:
            # Fix: convert skills to PostgreSQL array
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
    """Get vacancies from cache"""
    try:
        conn = get_db_connection()
        query = """
            SELECT * FROM vacancies 
            WHERE (name ILIKE %s OR description ILIKE %s)
            AND parsed_at > NOW() - (INTERVAL '1 hour' * %s)
            ORDER BY salary DESC LIMIT 100
        """
        # Fix: parameters passed as tuple
        df = pd.read_sql_query(query, conn, params=(f'%{text}%', f'%{text}%', hours))
        conn.close()
        return df if not df.empty else None
    except Exception as e:
        logger.error(f"CACHE READ ERROR | {e}")
        return None

def cluster_vacancies(df):
    """ML clustering by complexity"""
    if len(df) < 5:
        return df.assign(cluster="mixed")
    
    # Check for salary data
    if 'salary' not in df.columns or df['salary'].isna().all():
        return df.assign(cluster="unknown")
    
    # Filter rows with salary for mapping
    df = df.copy()
    df['description'] = df['description'].fillna('')
    df['skills'] = df['skills'].apply(lambda x: ' '.join(x) if isinstance(x, list) else str(x))
    
    text_data = df['description'] + ' ' + df['skills'].astype(str)
    vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    X = vectorizer.fit_transform(text_data)
    
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)
    
    # Correct mapping by salary
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

# FSM Handlers

@dp.message(SearchForm.waiting_profession)
async def process_profession(message: types.Message, state: FSMContext):
    await state.update_data(profession=message.text)
    await message.answer("Enter minimum salary (or /skip):")
    await state.set_state(SearchForm.waiting_salary_from)


@dp.message(SearchForm.waiting_salary_from)
async def process_salary_from(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_from=int(salary))
    await message.answer("Enter maximum salary (or /skip):")
    await state.set_state(SearchForm.waiting_salary_to)


@dp.message(SearchForm.waiting_salary_to)
async def process_salary_to(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_to=int(salary))
    await message.answer("Enter region (Moscow, SPb, Nizhny Novgorod, Kazan, Yekaterinburg):")
    await state.set_state(SearchForm.waiting_region)


# Callback handlers

@dp.callback_query(F.data == "analyze")
async def analyze_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter profession name:")
    await state.set_state(SearchForm.waiting_profession)
    await callback.answer()


@dp.callback_query(F.data == "ai_mode")
async def ai_mode_callback(callback: types.CallbackQuery, state: FSMContext):
    if not KILO_AUTO_API_KEY:
        await callback.message.answer("ERROR: KILO_AUTO_API_KEY not configured in .env")
    else:
        await callback.message.answer(
            "AI ANALYSIS\n\n"
            "Enter your question about the job market, salaries, or skills.\n\n"
            "Examples:\n"
            "• What skills does a Python developer need in 2024?\n"
            "• What is the average salary for a Junior JS developer?\n"
            "• IT market trends in Russia"
        )
        await state.set_state(AIForm.waiting_prompt)
    await callback.answer()


# AI message handler (alternative entry without FSM)
@dp.message(AIForm.waiting_prompt)
async def process_ai_prompt(message: types.Message, state: FSMContext):
    user_prompt = message.text
    
    logger.info(f"AI REQUEST | {message.from_user.full_name} | {user_prompt[:50]}...")
    
    await message.answer("Thinking...")
    
    response = await ask_kilo_auto(user_prompt)
    
    # Split long response into parts
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            await message.answer(response[i:i+4096])
    else:
        await message.answer(response)
    
    await state.clear()
    await state.set_state(None)


@dp.callback_query(F.data == "clusters")
async def clusters_callback(callback: types.CallbackQuery):
    await callback.message.answer("To view clusters, run search: /search Python")
    await callback.answer()


@dp.message(Command("ai"))
async def ai_command(message: types.Message, state: FSMContext):
    if not KILO_AUTO_API_KEY:
        await message.answer("ERROR: KILO_AUTO_API_KEY not configured in .env")
        return
    
    prompt = message.text.replace("/ai", "").strip()
    
    if not prompt:
        await message.answer(
            "AI ANALYSIS\n\n"
            "Enter your question about the job market:\n"
            "/ai What skills does a Python developer need?"
        )
        return
    
    logger.info(f"AI REQUEST | {message.from_user.full_name} | {prompt[:50]}...")
    
    await message.answer("Thinking...")
    
    response = await ask_kilo_auto(prompt)
    
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            await message.answer(response[i:i+4096])
    else:
        await message.answer(response)


@dp.message(Command("search"))
async def search_command(message: types.Message):
    """Quick search command: /search Python"""
    text = message.text.replace("/search", "").strip()
    
    if not text:
        await message.answer("Usage: /search <profession>\nExample: /search Python")
        return
    
    logger.info(f"QUICK SEARCH | {message.from_user.full_name} | {text}")
    
    await message.answer(f"Searching for: {text}...")
    
    try:
        # Check cache first
        cached = get_cached_vacancies(text)
        
        if cached is not None and not cached.empty:
            df = cached
            logger.info(f"CACHE HIT | '{text}' | {len(df)} vacancies")
        else:
            # Parse from HH (default: all regions)
            hh_df = parse_hh_vacancies(text, area=113)
            sj_df = parse_superjob_vacancies(text, town_id=4)
            
            df = pd.concat([hh_df, sj_df], ignore_index=True)
            
            if not df.empty:
                cache_vacancies(df)
                logger.info(f"CACHE SAVED | {len(df)} vacancies")
        
        if df.empty:
            await message.answer("No vacancies found")
        else:
            df = cluster_vacancies(df)
            
            result = f"Found: {len(df)} vacancies\n\n"
            for level in ["Junior", "Middle", "Senior", "mixed", "unknown"]:
                level_df = df[df['cluster'] == level]
                if not level_df.empty:
                    result += f"{level}: {len(level_df)} vacancies\n"
            
            await message.answer(result)
            
            # Show first results (top 50)
            for i, vac in enumerate(df.head(50).iterrows(), 1):
                _, row = vac
                url = row.get('url', '')
                source = row.get('source', '?').upper()
                
                await message.answer(
                    f"{i}. {row['name']}\n"
                    f"Salary: {row.get('salary', 'N/A')} RUB\n"
                    f"Company: {row.get('company', 'N/A')}\n"
                    f"Source: {source}\n"
                    f"Link: {url}"
                )
                
            # If more than 50, show message
            if len(df) > 50:
                await message.answer(f"...and {len(df) - 50} more vacancies. Use /cache to view all.")
                
    except TimeoutError:
        await message.answer("Timeout. Try again later.")
    except ConnectionError:
        await message.answer("Connection error. Check internet and try again.")
    except Exception as e:
        logger.error(f"SEARCH ERROR | {e}")
        await message.answer(f"Error: {str(e)[:100]}")


@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "Available commands:\n\n"
        "/start - Main menu\n"
        "/search <profession> - Quick search (e.g., /search Python)\n"
        "/cache - Show cached vacancies\n"
        "/ai <question> - AI analysis (requires KILO_AUTO_API_KEY)\n"
        "\nExamples:\n"
        "/search Java Moscow\n"
        "/search Frontend 150000"
    )


@dp.message(Command("cache"))
async def cache_command(message: types.Message):
    """Show all cached vacancies"""
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(
            "SELECT name, salary, company, source, url, parsed_at FROM vacancies ORDER BY parsed_at DESC LIMIT 100",
            conn
        )
        conn.close()
        
        if df.empty:
            await message.answer("Cache is empty. Use /search first.")
            return
        
        await message.answer(f"Cache: {len(df)} vacancies\n")
        
        for i, row in df.head(50).iterrows():
            url = row.get('url', '')
            source = row.get('source', '?').upper()
            parsed = row.get('parsed_at', '')
            
            await message.answer(
                f"{i+1}. {row['name']}\n"
                f"Salary: {row.get('salary', 'N/A')} RUB\n"
                f"Company: {row.get('company', 'N/A')}\n"
                f"Source: {source}\n"
                f"Link: {url}\n"
                f"Parsed: {parsed}"
            )
        
        if len(df) > 50:
            await message.answer(f"...and {len(df) - 50} more in cache.")
            
    except Exception as e:
        logger.error(f"CACHE ERROR | {e}")
        await message.answer(f"Error reading cache: {str(e)[:100]}")


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    logger.info(f"START command | {message.from_user.full_name}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Vacancy Analysis HH+SuperJob", callback_data="analyze")],
        [InlineKeyboardButton(text="AI Analysis", callback_data="ai_mode")],
        [InlineKeyboardButton(text="Complexity Clusters", callback_data="clusters")]
    ])
    
    await message.answer(
        "Vacancy Analyzer PRO\n"
        "HH.ru + SuperJob\n"
        "PostgreSQL cache (24h)\n"
        "ML clustering\n"
        "AI analysis\n"
        "_Default: Nizhny Novgorod_",
        reply_markup=keyboard
    )


@dp.message(SearchForm.waiting_region)
async def process_region(message: types.Message, state: FSMContext):
    data = await state.get_data()
    region = message.text.title()
    area = AREAS.get(region, AREAS["Нижний Новгород"])
    
    await state.update_data(area=area, region=region)
    await message.answer("Searching HH.ru + SuperJob...")
    
    # Perform search
    profession = data.get("profession", "")
    salary_from = data.get("salary_from")
    salary_to = data.get("salary_to")
    
    logger.info(f"SEARCH | profession: '{profession}' | region: {region} | salary: {salary_from}-{salary_to}")
    
    try:
        # Check cache
        cached = get_cached_vacancies(profession)
        
        if cached is not None and not cached.empty:
            df = cached
            logger.info(f"CACHE HIT | '{profession}' | {len(df)} vacancies")
        else:
            # Parse from HH and SuperJob
            logger.info(f"PARSING HH.ru | profession: '{profession}'")
            hh_df = parse_hh_vacancies(profession, area=area.get("hh"), salary_from=salary_from, salary_to=salary_to)
            logger.info(f"PARSING SuperJob | profession: '{profession}'")
            sj_df = parse_superjob_vacancies(profession, town_id=area.get("sj", 4), payment_from=salary_from, payment_to=salary_to)
            
            df = pd.concat([hh_df, sj_df], ignore_index=True)
            
            if not df.empty:
                cache_vacancies(df)
                logger.info(f"CACHE SAVED | {len(df)} vacancies")
        
        if df.empty:
            await message.answer("No vacancies found")
        else:
            # Clustering
            df = cluster_vacancies(df)
            
            # Format response
            result = f"Found: {len(df)} vacancies\n\n"
            for level in ["Junior", "Middle", "Senior", "mixed", "unknown"]:
                level_df = df[df['cluster'] == level]
                if not level_df.empty:
                    result += f"{level}: {len(level_df)} vacancies\n"
            
            await message.answer(result)
            
            # Show first results (top 50)
            for i, vac in enumerate(df.head(50).iterrows(), 1):
                _, row = vac
                url = row.get('url', '')
                source = row.get('source', '?').upper()
                
                await message.answer(
                    f"{i}. {row['name']}\n"
                    f"Salary: {row.get('salary', 'N/A')} RUB\n"
                    f"Company: {row.get('company', 'N/A')}\n"
                    f"Source: {source}\n"
                    f"Link: {url}"
                )
                
            # If more than 50, show message
            if len(df) > 50:
                await message.answer(f"...and {len(df) - 50} more vacancies. Use /cache to view all.")
                
    except TimeoutError as e:
        logger.error(f"TIMEOUT | {e}")
        await message.answer("Timeout waiting for server response. Try again later or repeat the request.")
    except ConnectionError as e:
        logger.error(f"CONNECTION ERROR | {e}")
        await message.answer("Failed to connect to job search server. Check internet connection and try again later.")
    except Exception as e:
        logger.error(f"SEARCH ERROR | {e}")
        await message.answer(f"Error occurred during search: {str(e)[:100]}")
    
    # Finish state
    await state.clear()
    await state.set_state(None)


async def main():
    logger.info("Starting Vacancy Analyzer PRO...")
    logger.info(f"Bot token: {BOT_TOKEN[:15]}...")
    logger.info(f"DB: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database connected and initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
    
    logger.info("Bot is polling for updates...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())