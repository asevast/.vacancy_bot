import asyncio
import sys
import re
from datetime import datetime, timedelta
import pandas as pd

from aiogram import Bot, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.config import (
    BOT_TOKEN,
    KILO_AUTO_API_KEY,
    SUBSCRIPTION_POLL_SECONDS,
    LIST_PAGE_SIZE,
    JOOBLE_API_KEY,
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    logger
)
from app.context import bot, dp
from app.utils import (
    parse_search_options,
    normalize_region_input,
    needs_clarification,
    apply_clarification
)
from app.db import (
    get_db_connection,
    init_db,
    cache_vacancies,
    safe_cache_vacancies,
    get_cached_vacancies,
    get_cached_vacancies_since,
    add_subscription,
    list_subscriptions,
    deactivate_subscription,
    update_subscription_last_sent
)
from app.api import (
    parse_hh_vacancies,
    parse_superjob_vacancies,
    parse_habr_vacancies,
    parse_aggregator_vacancies,
    parse_jooble_vacancies,
    parse_adzuna_vacancies
)
from app.ml import cluster_vacancies
from app.ai import ask_kilo_auto
from app.lists import (
    create_list_token,
    get_list_items,
    build_page_keyboard,
    format_vacancy_page,
    build_web_list_link
)
from app.profile import (
    get_user_profile,
    upsert_user_profile,
    normalize_level,
    normalize_format,
    parse_technologies,
    profile_summary
)
from app.analytics import compute_market_stats, format_market_stats


# Регионы (HH ID : SJ ID)
AREAS = {
    "Москва": {"hh": 1, "sj": 4},
    "СПб": {"hh": 2, "sj": 2}, 
    "Нижний Новгород": {"hh": 56, "sj": 64},
    "Екатеринбург": {"hh": 2101, "sj": 3},
    "Казань": {"hh": 35, "sj": 25},
    "Все": {"hh": 113, "sj": None}
}


def log_callback(func):
    async def wrapper(callback: types.CallbackQuery, state: FSMContext = None):
        user = callback.from_user
        logger.info(f"CALLBACK | {user.full_name} (@{user.username or 'N/A'}) | {callback.data}")
        if state:
            return await func(callback, state)
        return await func(callback)
    return wrapper


def log_message(func):
    async def wrapper(message: types.Message, state: FSMContext = None):
        user = message.from_user
        logger.info(f"MESSAGE | {user.full_name} (@{user.username or 'N/A'}) | {message.text}")
        if state:
            return await func(message, state)
        return await func(message)
    return wrapper


def _get_ask_kilo_auto():
    mod = sys.modules.get("vacancy_bot")
    if mod and hasattr(mod, "ask_kilo_auto"):
        return getattr(mod, "ask_kilo_auto")
    return ask_kilo_auto


def _safe_get_profile(user_id):
    if not user_id:
        return None
    try:
        return get_user_profile(user_id)
    except Exception as e:
        logger.error(f"PROFILE LOAD ERROR | {e}")
        return None


def _apply_profile_filters(df, level=None, work_format=None, technologies=None):
    if df is None or df.empty:
        return df
    filtered = df
    if level:
        filtered = filtered[filtered["experience"].astype(str).str.contains(str(level), case=False, na=False)]
    if work_format:
        filtered = filtered[filtered["description"].astype(str).str.contains(str(work_format), case=False, na=False)]
    if technologies:
        tech_list = [t for t in technologies if t]
        if tech_list:
            pattern = "|".join([re.escape(t) for t in tech_list])
            combined = filtered["description"].astype(str) + " " + filtered["skills"].astype(str)
            filtered = filtered[combined.str.contains(pattern, case=False, na=False)]
    return filtered


class SearchForm(StatesGroup):
    waiting_profession = State()
    waiting_clarification = State()
    waiting_salary_from = State()
    waiting_salary_to = State()
    waiting_region = State()
    waiting_confirmation = State()


class AIForm(StatesGroup):
    waiting_prompt = State()


class SubscribeForm(StatesGroup):
    waiting_profession = State()
    waiting_clarification = State()
    waiting_salary_from = State()
    waiting_salary_to = State()
    waiting_region = State()


class ProfileForm(StatesGroup):
    waiting_region = State()
    waiting_salary_from = State()
    waiting_salary_to = State()
    waiting_level = State()
    waiting_format = State()
    waiting_technologies = State()


async def send_subscription_digest(bot_instance, sub_row):
    user_id = int(sub_row["user_id"])
    sub_id = int(sub_row["id"])
    profession = sub_row["profession"]
    region = sub_row.get("region")
    salary_from = sub_row.get("salary_from")
    salary_to = sub_row.get("salary_to")
    last_sent_at = sub_row.get("last_sent_at")

    since_dt = last_sent_at if pd.notna(last_sent_at) else (datetime.utcnow() - timedelta(hours=24))

    df = get_cached_vacancies_since(profession, since_dt, region=region, salary_from=salary_from, salary_to=salary_to)
    if df is None or df.empty:
        area = AREAS.get(region, AREAS["Нижний Новгород"])
        hh_df = parse_hh_vacancies(profession, area=area.get("hh"), salary_from=salary_from, salary_to=salary_to, region_label=region)
        sj_df = parse_superjob_vacancies(profession, town_id=area.get("sj", 4), payment_from=salary_from, payment_to=salary_to, region_label=region)
        df = pd.concat([hh_df, sj_df], ignore_index=True)
        if not df.empty:
            safe_cache_vacancies(df)
        df = get_cached_vacancies_since(profession, since_dt, region=region, salary_from=salary_from, salary_to=salary_to)

    if df is None or df.empty:
        await bot_instance.send_message(user_id, f"Нет новых вакансий для '{profession}' с прошлого дайджеста.")
        update_subscription_last_sent(sub_id)
        return

    df = cluster_vacancies(df)
    await bot_instance.send_message(user_id, f"Дайджест по '{profession}': {len(df)} новых вакансий.")

    for i, row in enumerate(df.head(10).itertuples(index=False), 1):
        await bot_instance.send_message(
            user_id,
            f"{i}. {row.name}\n"
            f"Зарплата: {getattr(row, 'salary', 'N/A')} RUB\n"
            f"Компания: {getattr(row, 'company', 'N/A')}\n"
            f"Источник: {getattr(row, 'source', '?').upper()}\n"
            f"Ссылка: {getattr(row, 'url', '')}"
        )

    if len(df) > 10:
        await bot_instance.send_message(user_id, f"...и еще {len(df) - 10} вакансий.")

    update_subscription_last_sent(sub_id)


async def subscription_worker(bot_instance):
    while True:
        try:
            conn = get_db_connection()
            subs_df = pd.read_sql_query(
                '''
                SELECT id, user_id, profession, region, salary_from, salary_to, active, last_sent_at
                FROM subscriptions
                WHERE active = TRUE
                ORDER BY created_at ASC
                ''',
                conn
            )
            conn.close()

            if not subs_df.empty:
                for _, sub_row in subs_df.iterrows():
                    try:
                        await send_subscription_digest(bot_instance, sub_row)
                    except Exception as e:
                        logger.error(f"SUBSCRIPTION ERROR | {e}")
        except Exception as e:
            logger.error(f"SUBSCRIPTION WORKER ERROR | {e}")

        await asyncio.sleep(SUBSCRIPTION_POLL_SECONDS)


@dp.message(SearchForm.waiting_profession)
async def process_profession(message: types.Message, state: FSMContext):
    profession = (message.text or "").strip()
    user_id = getattr(getattr(message, "from_user", None), "id", None)
    profile = _safe_get_profile(user_id)
    defaults = {
        "region": profile.get("region") if profile else None,
        "salary_from": profile.get("salary_from") if profile else None,
        "salary_to": profile.get("salary_to") if profile else None
    }
    await state.update_data(profession=profession)
    if any(v is not None for v in defaults.values()):
        await state.update_data(defaults=defaults)
    if needs_clarification(profession):
        await message.answer(
            "Запрос слишком общий. Уточните специализацию или стек.\n"
            "Примеры: Python backend, Java QA, Product manager.\n"
            "Можно /skip, чтобы оставить как есть."
        )
        await state.set_state(SearchForm.waiting_clarification)
        return
    if defaults.get("salary_from") is not None:
        await state.update_data(salary_from=defaults.get("salary_from"))
        await message.answer(f"Введите минимальную зарплату (или /skip). По умолчанию: {defaults.get('salary_from')}")
    else:
        await message.answer("Введите минимальную зарплату (или /skip):")
    await state.set_state(SearchForm.waiting_salary_from)


@dp.message(SearchForm.waiting_clarification)
async def process_profession_clarification(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not isinstance(data, dict):
        data = {}
    base = data.get("profession", "")
    clarified = apply_clarification(base, message.text)
    await state.update_data(profession=clarified)
    defaults = data.get("defaults", {})
    if defaults.get("salary_from") is not None:
        await state.update_data(salary_from=defaults.get("salary_from"))
        await message.answer(f"Введите минимальную зарплату (или /skip). По умолчанию: {defaults.get('salary_from')}")
    else:
        await message.answer("Введите минимальную зарплату (или /skip):")
    await state.set_state(SearchForm.waiting_salary_from)


@dp.message(SearchForm.waiting_salary_from)
async def process_salary_from(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not isinstance(data, dict):
        data = {}
    defaults = data.get("defaults", {})
    if message.text == "/skip" and defaults.get("salary_from") is not None:
        await state.update_data(salary_from=defaults.get("salary_from"))
    elif message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_from=int(salary))
    if defaults.get("salary_to") is not None:
        await message.answer(f"Введите максимальную зарплату (или /skip). По умолчанию: {defaults.get('salary_to')}")
    else:
        await message.answer("Введите максимальную зарплату (или /skip):")
    await state.set_state(SearchForm.waiting_salary_to)


@dp.message(SearchForm.waiting_salary_to)
async def process_salary_to(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not isinstance(data, dict):
        data = {}
    defaults = data.get("defaults", {})
    if message.text == "/skip" and defaults.get("salary_to") is not None:
        await state.update_data(salary_to=defaults.get("salary_to"))
    elif message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_to=int(salary))
    if defaults.get("region"):
        await message.answer(f"Введите регион (Москва, СПб, Нижний Новгород, Казань, Екатеринбург) или /skip. По умолчанию: {defaults.get('region')}")
    else:
        await message.answer("Введите регион (Москва, СПб, Нижний Новгород, Казань, Екатеринбург):")
    await state.set_state(SearchForm.waiting_region)


@dp.message(Command("subscribe"))
async def subscribe_command(message: types.Message, state: FSMContext):
    await message.answer("Подписка: введите название профессии:")
    await state.set_state(SubscribeForm.waiting_profession)


@dp.message(SubscribeForm.waiting_profession)
async def subscribe_profession(message: types.Message, state: FSMContext):
    profession = (message.text or "").strip()
    user_id = getattr(getattr(message, "from_user", None), "id", None)
    profile = _safe_get_profile(user_id)
    defaults = {
        "region": profile.get("region") if profile else None,
        "salary_from": profile.get("salary_from") if profile else None,
        "salary_to": profile.get("salary_to") if profile else None
    }
    await state.update_data(profession=profession, defaults=defaults)
    if needs_clarification(profession):
        await message.answer(
            "Запрос слишком общий. Уточните специализацию или стек.\n"
            "Примеры: Python backend, Java QA, Product manager.\n"
            "Можно /skip, чтобы оставить как есть."
        )
        await state.set_state(SubscribeForm.waiting_clarification)
        return
    if defaults.get("salary_from") is not None:
        await state.update_data(salary_from=defaults.get("salary_from"))
        await message.answer(f"Введите минимальную зарплату (или /skip). По умолчанию: {defaults.get('salary_from')}")
    else:
        await message.answer("Введите минимальную зарплату (или /skip):")
    await state.set_state(SubscribeForm.waiting_salary_from)


@dp.message(SubscribeForm.waiting_clarification)
async def subscribe_profession_clarification(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not isinstance(data, dict):
        data = {}
    base = data.get("profession", "")
    clarified = apply_clarification(base, message.text)
    await state.update_data(profession=clarified)
    defaults = data.get("defaults")
    if not defaults:
        user_id = getattr(getattr(message, "from_user", None), "id", None)
        profile = _safe_get_profile(user_id)
        defaults = {
            "region": profile.get("region") if profile else None,
            "salary_from": profile.get("salary_from") if profile else None,
            "salary_to": profile.get("salary_to") if profile else None
        }
        await state.update_data(defaults=defaults)
    if defaults.get("salary_from") is not None:
        await state.update_data(salary_from=defaults.get("salary_from"))
        await message.answer(f"Введите минимальную зарплату (или /skip). По умолчанию: {defaults.get('salary_from')}")
    else:
        await message.answer("Введите минимальную зарплату (или /skip):")
    await state.set_state(SubscribeForm.waiting_salary_from)


@dp.message(SubscribeForm.waiting_salary_from)
async def subscribe_salary_from(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not isinstance(data, dict):
        data = {}
    defaults = data.get("defaults", {})
    if message.text == "/skip" and defaults.get("salary_from") is not None:
        await state.update_data(salary_from=defaults.get("salary_from"))
    elif message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_from=int(salary))
    if defaults.get("salary_to") is not None:
        await message.answer(f"Введите максимальную зарплату (или /skip). По умолчанию: {defaults.get('salary_to')}")
    else:
        await message.answer("Введите максимальную зарплату (или /skip):")
    await state.set_state(SubscribeForm.waiting_salary_to)


@dp.message(SubscribeForm.waiting_salary_to)
async def subscribe_salary_to(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not isinstance(data, dict):
        data = {}
    defaults = data.get("defaults", {})
    if message.text == "/skip" and defaults.get("salary_to") is not None:
        await state.update_data(salary_to=defaults.get("salary_to"))
    elif message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_to=int(salary))
    if defaults.get("region"):
        await message.answer(f"Введите регион (Москва, СПб, Нижний Новгород, Казань, Екатеринбург или Все) или /skip. По умолчанию: {defaults.get('region')}")
    else:
        await message.answer("Введите регион (Москва, СПб, Нижний Новгород, Казань, Екатеринбург или Все):")
    await state.set_state(SubscribeForm.waiting_region)


@dp.message(SubscribeForm.waiting_region)
async def subscribe_region(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not isinstance(data, dict):
        data = {}
    defaults = data.get("defaults", {})
    if message.text == "/skip" and defaults.get("region"):
        region = defaults.get("region")
    else:
        region = normalize_region_input(message.text)
    profession = data.get("profession", "")
    salary_from = data.get("salary_from")
    salary_to = data.get("salary_to")

    sub_id = add_subscription(
        user_id=message.from_user.id,
        profession=profession,
        region=region,
        salary_from=salary_from,
        salary_to=salary_to
    )

    await message.answer(
        f"Подписка создана (id={sub_id}).\n"
        f"Профессия: {profession}\n"
        f"Регион: {region}\n"
        f"Зарплата: {salary_from}-{salary_to}"
    )

    await state.clear()
    await state.set_state(None)


@dp.message(Command("subscriptions"))
async def subscriptions_command(message: types.Message):
    df = list_subscriptions(message.from_user.id)
    if df.empty:
        await message.answer("Подписок пока нет. Используйте /subscribe.")
        return

    lines = ["Ваши подписки:"]
    for row in df.itertuples(index=False):
        lines.append(
            f"#{row.id} | {row.profession} | {row.region or 'All'} | "
            f"{row.salary_from or '-'}-{row.salary_to or '-'} | "
            f"{'активна' if row.active else 'неактивна'}"
        )
    await message.answer("\n".join(lines))


@dp.message(Command("unsubscribe"))
async def unsubscribe_command(message: types.Message):
    text = message.text.replace("/unsubscribe", "").strip()
    if not text.isdigit():
        await message.answer("Использование: /unsubscribe <id>")
        return
    deactivate_subscription(message.from_user.id, int(text))
    await message.answer(f"Подписка {text} отключена.")


@dp.message(Command("digest"))
async def digest_command(message: types.Message):
    df = list_subscriptions(message.from_user.id)
    df = df[df["active"] == True]  # noqa: E712
    if df.empty:
        await message.answer("Нет активных подписок для дайджеста.")
        return
    for _, row in df.iterrows():
        await send_subscription_digest(bot or Bot(token=BOT_TOKEN), row)


@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    user_id = getattr(getattr(message, "from_user", None), "id", None)
    profile = _safe_get_profile(user_id)
    await message.answer(profile_summary(profile))


@dp.message(Command("profile_set"))
async def profile_set_command(message: types.Message, state: FSMContext):
    await message.answer("Настройка профиля. Введите регион (Москва, СПб, Нижний Новгород, Казань, Екатеринбург или Все):")
    await state.set_state(ProfileForm.waiting_region)


@dp.message(ProfileForm.waiting_region)
async def profile_region(message: types.Message, state: FSMContext):
    if message.text == "/skip":
        region = None
    else:
        region = normalize_region_input(message.text)
    await state.update_data(region=region)
    await message.answer("Введите минимальную зарплату (или /skip):")
    await state.set_state(ProfileForm.waiting_salary_from)


@dp.message(ProfileForm.waiting_salary_from)
async def profile_salary_from(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_from=int(salary))
    await message.answer("Введите максимальную зарплату (или /skip):")
    await state.set_state(ProfileForm.waiting_salary_to)


@dp.message(ProfileForm.waiting_salary_to)
async def profile_salary_to(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        salary = message.text.replace(" ", "").replace("₽", "")
        if salary.isdigit():
            await state.update_data(salary_to=int(salary))
    await message.answer("Введите уровень (junior/middle/senior/lead) или /skip:")
    await state.set_state(ProfileForm.waiting_level)


@dp.message(ProfileForm.waiting_level)
async def profile_level(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(level=normalize_level(message.text))
    await message.answer("Введите формат (remote/hybrid/office) или /skip:")
    await state.set_state(ProfileForm.waiting_format)


@dp.message(ProfileForm.waiting_format)
async def profile_format(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(work_format=normalize_format(message.text))
    await message.answer("Введите любимые технологии через запятую (или /skip):")
    await state.set_state(ProfileForm.waiting_technologies)


@dp.message(ProfileForm.waiting_technologies)
async def profile_technologies(message: types.Message, state: FSMContext):
    technologies = []
    if message.text != "/skip":
        technologies = parse_technologies(message.text)
    data = await state.get_data()
    upsert_user_profile(
        user_id=message.from_user.id,
        region=data.get("region"),
        salary_from=data.get("salary_from"),
        salary_to=data.get("salary_to"),
        level=data.get("level"),
        work_format=data.get("work_format"),
        technologies=technologies or None
    )
    user_id = getattr(getattr(message, "from_user", None), "id", None)
    profile = _safe_get_profile(user_id)
    await message.answer("Профиль сохранен.\n\n" + profile_summary(profile))
    await state.clear()
    await state.set_state(None)


@dp.callback_query(F.data == "analyze")
async def analyze_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название профессии:")
    await state.set_state(SearchForm.waiting_profession)
    await callback.answer()


@dp.callback_query(F.data == "ai_mode")
async def ai_mode_callback(callback: types.CallbackQuery, state: FSMContext):
    if not KILO_AUTO_API_KEY:
        await callback.message.answer("ОШИБКА: KILO_AUTO_API_KEY не настроен в .env")
    else:
        await callback.message.answer(
            "AI АНАЛИЗ\n\n"
            "Введите вопрос о рынке труда, зарплатах или навыках.\n\n"
            "Примеры:\n"
            "• Какие навыки нужны Python разработчику в 2024?\n"
            "• Какая средняя зарплата Junior JS разработчика?\n"
            "• Тренды IT рынка в России"
        )
        await state.set_state(AIForm.waiting_prompt)
    await callback.answer()


@dp.message(AIForm.waiting_prompt)
async def process_ai_prompt(message: types.Message, state: FSMContext):
    user_prompt = message.text
    
    logger.info(f"AI REQUEST | {message.from_user.full_name} | {user_prompt[:50]}...")
    
    await message.answer("Думаю...")
    
    response = await _get_ask_kilo_auto()(user_prompt)
    if response is None:
        response = "Ошибка: пустой ответ от AI. Попробуйте позже."
    
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            await message.answer(response[i:i+4096])
    else:
        await message.answer(response)
    
    await state.clear()
    await state.set_state(None)


@dp.callback_query(F.data == "clusters")
async def clusters_callback(callback: types.CallbackQuery):
    await callback.message.answer("Чтобы увидеть кластеры, выполните поиск: /search Python")
    await callback.answer()


@dp.callback_query(F.data.startswith("page:"))
async def page_callback(callback: types.CallbackQuery):
    try:
        _, token, page_str = callback.data.split(":", 2)
        page = int(page_str)
    except Exception:
        await callback.answer("Некорректная страница", show_alert=True)
        return

    items = get_list_items(token)
    if not items:
        await callback.answer("Список истек", show_alert=True)
        return

    text, total_pages = format_vacancy_page(items, page, LIST_PAGE_SIZE)
    keyboard = build_page_keyboard(token, page, total_pages)
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@dp.message(Command("ai"))
async def ai_command(message: types.Message, state: FSMContext):
    if not KILO_AUTO_API_KEY:
        await message.answer("ОШИБКА: KILO_AUTO_API_KEY не настроен в .env")
        return
    
    prompt = message.text.replace("/ai", "").strip()
    
    if not prompt:
        await message.answer(
            "AI АНАЛИЗ\n\n"
            "Введите вопрос о рынке труда:\n"
            "/ai Какие навыки нужны Python разработчику?"
        )
        return
    
    logger.info(f"AI REQUEST | {message.from_user.full_name} | {prompt[:50]}...")
    
    await message.answer("Думаю...")
    
    response = await _get_ask_kilo_auto()(prompt)
    if response is None:
        response = "Ошибка: пустой ответ от AI. Попробуйте позже."
    
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            await message.answer(response[i:i+4096])
    else:
        await message.answer(response)


@dp.message(Command("search"))
async def search_command(message: types.Message):
    """Quick search command: /search Python"""
    text = message.text.replace("/search", "").strip()
    profession, opts = parse_search_options(text)
    
    if not profession:
        await message.answer("Использование: /search <профессия> [опции]\nПример: /search Python region=Москва salary_from=100000 order=salary_desc")
        return
    if needs_clarification(profession):
        await message.answer(
            "Запрос слишком общий. Уточните специализацию или стек.\n"
            "Пример: /search Python backend region=Москва\n"
            "Для пошагового уточнения используйте /start."
        )
        return
    
    logger.info(f"QUICK SEARCH | {message.from_user.full_name} | {profession} | {opts}")
    
    await message.answer(f"Ищу: {profession}...")
    
    try:
        user_id = getattr(getattr(message, "from_user", None), "id", None)
        profile = _safe_get_profile(user_id)
        defaults = {
            "region": profile.get("region") if profile else None,
            "salary_from": profile.get("salary_from") if profile else None,
            "salary_to": profile.get("salary_to") if profile else None,
            "level": profile.get("level") if profile else None,
            "work_format": profile.get("work_format") if profile else None,
            "technologies": profile.get("technologies") if profile else None
        }

        region = normalize_region_input(opts.get("region")) if opts.get("region") else (defaults.get("region") or "Все")
        area = AREAS.get(region, AREAS["Нижний Новгород"])

        salary_from = int(opts["salary_from"]) if opts.get("salary_from", "").isdigit() else defaults.get("salary_from")
        salary_to = int(opts["salary_to"]) if opts.get("salary_to", "").isdigit() else defaults.get("salary_to")

        source = opts.get("source")
        order = opts.get("order", "salary_desc").lower()
        limit = int(opts["limit"]) if opts.get("limit", "").isdigit() else 50

        experience = opts.get("experience")
        employment = opts.get("employment")
        schedule = opts.get("schedule")
        professional_role = opts.get("professional_role")
        search_field = opts.get("search_field")
        period = opts.get("period")
        currency = opts.get("currency")
        label = opts.get("label")
        order_by = opts.get("order_by")
        page = int(opts["page"]) if opts.get("page", "").isdigit() else None
        only_with_salary = opts.get("only_with_salary") in {"1", "true", "yes"}
        level = opts.get("level") or defaults.get("level")
        work_format = opts.get("format") or defaults.get("work_format")
        technologies = defaults.get("technologies") or []

        cached = get_cached_vacancies(profession, region=region, salary_from=salary_from, salary_to=salary_to)
        
        if cached is not None and not cached.empty:
            df = cached
            logger.info(f"CACHE HIT | '{profession}' | {len(df)} vacancies")
        else:
            hh_df = pd.DataFrame()
            sj_df = pd.DataFrame()
            if source in (None, "hh"):
                hh_df = parse_hh_vacancies(
                    profession,
                    area=area.get("hh"),
                    salary_from=salary_from,
                    salary_to=salary_to,
                    region_label=region,
                    experience=experience,
                    employment=employment,
                    only_with_salary=only_with_salary,
                    schedule=schedule,
                    professional_role=professional_role,
                    search_field=search_field,
                    period=period,
                    currency=currency,
                    label=label,
                    order_by=order_by,
                    page=page
                )
            if source in (None, "sj"):
                sj_df = parse_superjob_vacancies(
                    profession,
                    town_id=area.get("sj", 4),
                    payment_from=salary_from,
                    payment_to=salary_to,
                    region_label=region
                )
            if source in (None, "habr"):
                habr_df = parse_habr_vacancies(
                    profession,
                    count=limit,
                    region_label=region
                )
            else:
                habr_df = pd.DataFrame()
            if source in (None, "jooble"):
                jooble_df = parse_jooble_vacancies(
                    profession,
                    count=limit,
                    region_label=region
                )
            else:
                jooble_df = pd.DataFrame()
            if source in (None, "adzuna"):
                adzuna_df = parse_adzuna_vacancies(
                    profession,
                    count=limit,
                    region_label=region
                )
            else:
                adzuna_df = pd.DataFrame()
            if source in (None, "agg"):
                agg_df = parse_aggregator_vacancies(
                    profession,
                    count=limit,
                    region_label=region
                )
            else:
                agg_df = pd.DataFrame()
            
            df = pd.concat([hh_df, sj_df, habr_df, jooble_df, adzuna_df, agg_df], ignore_index=True)

            df = _apply_profile_filters(df, level=level, work_format=work_format, technologies=technologies)
            
            if not df.empty:
                safe_cache_vacancies(df)
                logger.info(f"CACHE SAVED | {len(df)} vacancies")

        df = _apply_profile_filters(df, level=level, work_format=work_format, technologies=technologies)
        
        if df.empty:
            await message.answer("Вакансии не найдены")
        else:
            df = cluster_vacancies(df)

            if order == "salary_asc":
                df = df.sort_values(by="salary", ascending=True, na_position="last")
            elif order == "salary_desc":
                df = df.sort_values(by="salary", ascending=False, na_position="last")
            
            result = f"Найдено вакансий: {len(df)}\n\n"
            for level in ["Junior", "Middle", "Senior", "mixed", "unknown"]:
                level_df = df[df['cluster'] == level]
                if not level_df.empty:
                    result += f"{level}: {len(level_df)}\n"
            
            await message.answer(result)
            
            items = df.to_dict(orient="records")
            if len(items) > 10:
                token = create_list_token(items)
                link = build_web_list_link(token)
                text, total_pages = format_vacancy_page(items, 1, LIST_PAGE_SIZE)
                keyboard = build_page_keyboard(token, 1, total_pages)
                await message.answer(f"Полный список: {link}")
                await message.answer(text, reply_markup=keyboard)
            else:
                limit = max(1, min(limit, 100))
                for i, vac in enumerate(df.head(limit).iterrows(), 1):
                    _, row = vac
                    url = row.get('url', '')
                    source = row.get('source', '?').upper()
                    
                    await message.answer(
                        f"{i}. {row['name']}\n"
                        f"Зарплата: {row.get('salary', 'N/A')} RUB\n"
                        f"Компания: {row.get('company', 'N/A')}\n"
                        f"Источник: {source}\n"
                        f"Ссылка: {url}"
                    )
                
    except TimeoutError:
        await message.answer("Таймаут. Попробуйте позже.")
    except ConnectionError:
        await message.answer("Ошибка соединения. Проверьте интернет и повторите.")
    except Exception as e:
        logger.error(f"SEARCH ERROR | {e}")
        await message.answer(f"Ошибка: {str(e)[:100]}")


@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "Доступные команды:\n\n"
        "/start - Главное меню\n"
        "/search <профессия> [опции] - Быстрый поиск (например, /search Python region=Москва salary_from=100000 order=salary_desc)\n"
        "/stats <профессия> [опции] - Аналитика рынка по запросу\n"
        "/cache - Показать кэш\n"
        "/subscribe - Создать подписку (FSM)\n"
        "/subscriptions - Список подписок\n"
        "/unsubscribe <id> - Отключить подписку\n"
        "/digest - Получить дайджест сейчас\n"
        "/profile - Показать профиль\n"
        "/profile_set - Настроить профиль\n"
        "/sources - Источники и настройка токенов\n"
        "/ai <вопрос> - AI анализ (нужен KILO_AUTO_API_KEY)\n"
        "\nПримеры:\n"
        "/search Java region=Москва salary_from=150000\n"
        "/search Frontend order=salary_asc limit=20\n"
        "/search DevOps source=hh experience=between1And3 only_with_salary=1\n"
        "/search Python source=habr\n"
        "/search Go source=jooble\n"
        "/search Rust source=adzuna\n"
        "/search Golang source=agg\n"
        "/stats Python region=Москва"
    )


@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    text = message.text.replace("/stats", "").strip()
    profession, opts = parse_search_options(text)

    if not profession:
        await message.answer("Использование: /stats <профессия> [опции]")
        return

    await message.answer(f"Собираю аналитику: {profession}...")

    try:
        user_id = getattr(getattr(message, "from_user", None), "id", None)
        profile = _safe_get_profile(user_id)
        defaults = {
            "region": profile.get("region") if profile else None,
            "salary_from": profile.get("salary_from") if profile else None,
            "salary_to": profile.get("salary_to") if profile else None,
            "level": profile.get("level") if profile else None,
            "work_format": profile.get("work_format") if profile else None,
            "technologies": profile.get("technologies") if profile else None
        }

        region = normalize_region_input(opts.get("region")) if opts.get("region") else (defaults.get("region") or "Все")
        area = AREAS.get(region, AREAS["Нижний Новгород"])
        salary_from = int(opts["salary_from"]) if opts.get("salary_from", "").isdigit() else defaults.get("salary_from")
        salary_to = int(opts["salary_to"]) if opts.get("salary_to", "").isdigit() else defaults.get("salary_to")
        source = opts.get("source")
        limit = int(opts["limit"]) if opts.get("limit", "").isdigit() else 50

        experience = opts.get("experience")
        employment = opts.get("employment")
        schedule = opts.get("schedule")
        professional_role = opts.get("professional_role")
        search_field = opts.get("search_field")
        period = opts.get("period")
        currency = opts.get("currency")
        label = opts.get("label")
        order_by = opts.get("order_by")
        page = int(opts["page"]) if opts.get("page", "").isdigit() else None
        only_with_salary = opts.get("only_with_salary") in {"1", "true", "yes"}
        level = opts.get("level") or defaults.get("level")
        work_format = opts.get("format") or defaults.get("work_format")
        technologies = defaults.get("technologies") or []

        cached = get_cached_vacancies(profession, region=region, salary_from=salary_from, salary_to=salary_to)
        if cached is not None and not cached.empty:
            df = cached
        else:
            hh_df = pd.DataFrame()
            sj_df = pd.DataFrame()
            if source in (None, "hh"):
                hh_df = parse_hh_vacancies(
                    profession,
                    area=area.get("hh"),
                    salary_from=salary_from,
                    salary_to=salary_to,
                    region_label=region,
                    experience=experience,
                    employment=employment,
                    only_with_salary=only_with_salary,
                    schedule=schedule,
                    professional_role=professional_role,
                    search_field=search_field,
                    period=period,
                    currency=currency,
                    label=label,
                    order_by=order_by,
                    page=page
                )
            if source in (None, "sj"):
                sj_df = parse_superjob_vacancies(
                    profession,
                    town_id=area.get("sj", 4),
                    payment_from=salary_from,
                    payment_to=salary_to,
                    region_label=region
                )
            habr_df = parse_habr_vacancies(profession, count=limit, region_label=region) if source in (None, "habr") else pd.DataFrame()
            jooble_df = parse_jooble_vacancies(profession, count=limit, region_label=region) if source in (None, "jooble") else pd.DataFrame()
            adzuna_df = parse_adzuna_vacancies(profession, count=limit, region_label=region) if source in (None, "adzuna") else pd.DataFrame()
            agg_df = parse_aggregator_vacancies(profession, count=limit, region_label=region) if source in (None, "agg") else pd.DataFrame()

            df = pd.concat([hh_df, sj_df, habr_df, jooble_df, adzuna_df, agg_df], ignore_index=True)
            if not df.empty:
                safe_cache_vacancies(df)

        df = _apply_profile_filters(df, level=level, work_format=work_format, technologies=technologies)
        if df.empty:
            await message.answer("Нет данных для аналитики.")
            return

        stats = compute_market_stats(df)
        await message.answer(format_market_stats(profession, stats))
    except TimeoutError:
        await message.answer("Таймаут. Попробуйте позже.")
    except ConnectionError:
        await message.answer("Ошибка соединения. Проверьте интернет и повторите.")
    except Exception as e:
        logger.error(f"STATS ERROR | {e}")
        await message.answer(f"Ошибка аналитики: {str(e)[:100]}")


@dp.message(Command("sources"))
async def sources_command(message: types.Message):
    jooble_status = "настроен" if JOOBLE_API_KEY else "не настроен"
    adzuna_status = "настроен" if (ADZUNA_APP_ID and ADZUNA_APP_KEY) else "не настроен"
    await message.answer(
        "Источники вакансий:\n"
        "• HH.ru (по умолчанию)\n"
        "• SuperJob (нужен SJ_API_KEY)\n"
        "• Habr Career (нужен HABR_API_TOKEN, HABR_API_URL опционально)\n"
        f"• Jooble (нужен JOOBLE_API_KEY) — {jooble_status}\n"
        f"• Adzuna (нужны ADZUNA_APP_ID и ADZUNA_APP_KEY) — {adzuna_status}\n"
        "• Агрегатор (нужны AGGREGATOR_API_URL и AGGREGATOR_API_TOKEN)\n\n"
        "Настройка токенов: откройте .env и заполните ключи, затем перезапустите бота.\n"
        "Подсказки по регистрации ключей:\n"
        "• Jooble: зарегистрируйтесь на сайте Jooble для получения API key.\n"
        "• Adzuna: зарегистрируйтесь в Adzuna Developer Portal и получите App ID и App Key.\n"
        "Подсказка: используйте /search ... source=hh|sj|habr|jooble|adzuna|agg"
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
            await message.answer("Кэш пуст. Сначала выполните /search.")
            return
        
        await message.answer(f"Кэш: {len(df)} вакансий\n")
        
        items = df.to_dict(orient="records")
        token = create_list_token(items)
        link = build_web_list_link(token)
        text, total_pages = format_vacancy_page(items, 1, LIST_PAGE_SIZE)
        keyboard = build_page_keyboard(token, 1, total_pages)
        await message.answer(f"Полный список: {link}")
        await message.answer(text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"CACHE ERROR | {e}")
        await message.answer(f"Ошибка чтения кэша: {str(e)[:100]}")


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    logger.info(f"START command | {message.from_user.full_name}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Анализ HH+SuperJob", callback_data="analyze")],
        [InlineKeyboardButton(text="🧠 AI Анализ", callback_data="ai_mode")],
        [InlineKeyboardButton(text="📊 Кластеры сложности", callback_data="clusters")]
    ])
    
    await message.answer(
        "🚀 Vacancy Analyzer PRO\n"
        "✅ HH.ru + SuperJob\n"
        "✅ PostgreSQL кэш (24ч)\n"
        "✅ ML кластеризация\n"
        "✅ AI анализ\n"
        "✅ Профиль пользователя (/profile_set)\n"
        "_Нижний Новгород по умолчанию_",
        reply_markup=keyboard
    )


@dp.message(SearchForm.waiting_region)
async def process_region(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not isinstance(data, dict):
        data = {}
    defaults = data.get("defaults", {})
    if message.text == "/skip" and defaults.get("region"):
        region = defaults.get("region")
    else:
        region = normalize_region_input(message.text)
    area = AREAS.get(region, AREAS["Нижний Новгород"])
    
    await state.update_data(area=area, region=region)
    await message.answer(
        "Проверьте запрос:\n"
        f"Профессия: {data.get('profession', '')}\n"
        f"Зарплата: {data.get('salary_from')}-{data.get('salary_to')}\n"
        f"Регион: {region}\n\n"
        "Ответьте: Да/Нет"
    )
    await state.set_state(SearchForm.waiting_confirmation)
    return


@dp.message(SearchForm.waiting_confirmation)
async def process_search_confirmation(message: types.Message, state: FSMContext):
    confirm = (message.text or "").strip().lower()
    if confirm in {"нет", "no", "n"}:
        await message.answer("Ок, начнем сначала. Введите профессию:")
        await state.set_state(SearchForm.waiting_profession)
        return

    if confirm not in {"да", "yes", "y"}:
        await message.answer("Пожалуйста, ответьте Да или Нет.")
        return

    data = await state.get_data()
    region = data.get("region")
    area = data.get("area")
    await message.answer("Ищу на HH.ru + SuperJob...")
    
    profession = data.get("profession", "")
    salary_from = data.get("salary_from")
    salary_to = data.get("salary_to")
    
    logger.info(f"SEARCH | profession: '{profession}' | region: {region} | salary: {salary_from}-{salary_to}")
    
    try:
        user_id = getattr(getattr(message, "from_user", None), "id", None)
        profile = _safe_get_profile(user_id)
        level = profile.get("level") if profile else None
        work_format = profile.get("work_format") if profile else None
        technologies = profile.get("technologies") if profile else []

        cached = get_cached_vacancies(profession, region=region, salary_from=salary_from, salary_to=salary_to)
        
        if cached is not None and not cached.empty:
            df = cached
            logger.info(f"CACHE HIT | '{profession}' | {len(df)} vacancies")
        else:
            logger.info(f"PARSING HH.ru | profession: '{profession}'")
            hh_df = parse_hh_vacancies(profession, area=area.get("hh"), salary_from=salary_from, salary_to=salary_to, region_label=region)
            logger.info(f"PARSING SuperJob | profession: '{profession}'")
            sj_df = parse_superjob_vacancies(profession, town_id=area.get("sj", 4), payment_from=salary_from, payment_to=salary_to, region_label=region)
            habr_df = parse_habr_vacancies(profession, count=50, region_label=region)
            jooble_df = parse_jooble_vacancies(profession, count=50, region_label=region)
            adzuna_df = parse_adzuna_vacancies(profession, count=50, region_label=region)
            agg_df = parse_aggregator_vacancies(profession, count=50, region_label=region)
            
            df = pd.concat([hh_df, sj_df, habr_df, jooble_df, adzuna_df, agg_df], ignore_index=True)
            
            if not df.empty:
                safe_cache_vacancies(df)
                logger.info(f"CACHE SAVED | {len(df)} vacancies")

        df = _apply_profile_filters(df, level=level, work_format=work_format, technologies=technologies)
        
        if df.empty:
            await message.answer("Вакансии не найдены")
        else:
            df = cluster_vacancies(df)
            
            result = f"Найдено вакансий: {len(df)}\n\n"
            for level in ["Junior", "Middle", "Senior", "mixed", "unknown"]:
                level_df = df[df['cluster'] == level]
                if not level_df.empty:
                    result += f"{level}: {len(level_df)}\n"
            
            await message.answer(result)
            if profile:
                await message.answer("Подсказка: профиль применяется как фильтр (уровень/формат/технологии). Изменить: /profile_set")
            
            items = df.to_dict(orient="records")
            if len(items) > 10:
                token = create_list_token(items)
                link = build_web_list_link(token)
                text, total_pages = format_vacancy_page(items, 1, LIST_PAGE_SIZE)
                keyboard = build_page_keyboard(token, 1, total_pages)
                await message.answer(f"Полный список: {link}")
                await message.answer(text, reply_markup=keyboard)
            else:
                for i, vac in enumerate(df.head(50).iterrows(), 1):
                    _, row = vac
                    url = row.get('url', '')
                    source = row.get('source', '?').upper()
                    
                    await message.answer(
                        f"{i}. {row['name']}\n"
                        f"Зарплата: {row.get('salary', 'N/A')} RUB\n"
                        f"Компания: {row.get('company', 'N/A')}\n"
                        f"Источник: {source}\n"
                        f"Ссылка: {url}"
                    )
                
    except TimeoutError as e:
        logger.error(f"TIMEOUT | {e}")
        await message.answer("Таймаут ожидания ответа. Попробуйте позже или повторите запрос.")
    except ConnectionError as e:
        logger.error(f"CONNECTION ERROR | {e}")
        await message.answer("Не удалось подключиться к серверу поиска. Проверьте интернет и попробуйте позже.")
    except Exception as e:
        logger.error(f"SEARCH ERROR | {e}")
        await message.answer(f"Ошибка при поиске: {str(e)[:100]}")
    
    await state.clear()
    await state.set_state(None)
