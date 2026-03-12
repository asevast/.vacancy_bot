import os
from datetime import datetime, timedelta
from aiohttp import web
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import (
    LIST_MAX_AGE_HOURS,
    LIST_PAGE_SIZE,
    PUBLIC_BASE_URL,
    WEB_HOST,
    WEB_PORT,
    logger
)

LIST_STORE = {}


def _cleanup_list_store():
    cutoff = datetime.utcnow() - timedelta(hours=LIST_MAX_AGE_HOURS)
    stale_keys = [k for k, v in LIST_STORE.items() if v.get("created_at") < cutoff]
    for key in stale_keys:
        LIST_STORE.pop(key, None)


def create_list_token(items):
    _cleanup_list_store()
    token = os.urandom(6).hex()
    LIST_STORE[token] = {"items": items, "created_at": datetime.utcnow()}
    return token


def get_list_items(token):
    _cleanup_list_store()
    record = LIST_STORE.get(token)
    return record.get("items") if record else None


def build_page_keyboard(token, page, total_pages):
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{token}:{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page:{token}:{page+1}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None


def format_vacancy_page(items, page, page_size):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    lines = [f"Страница {page}/{total_pages}"]
    for i, row in enumerate(items[start:end], start + 1):
        lines.append(
            f"{i}. {row.get('name')}\n"
            f"Зарплата: {row.get('salary', 'N/A')} RUB\n"
            f"Компания: {row.get('company', 'N/A')}\n"
            f"Источник: {row.get('source', '?').upper()}\n"
            f"Ссылка: {row.get('url', '')}"
        )
    return "\n\n".join(lines), total_pages


def build_web_list_link(token):
    return f"{PUBLIC_BASE_URL}/list/{token}"


async def list_page_handler(request):
    token = request.match_info.get("token")
    items = get_list_items(token)
    if not items:
        return web.Response(text="Список не найден или истек.", content_type="text/html")
    page = int(request.query.get("page", "1") or "1")
    page = max(1, page)
    total = len(items)
    total_pages = max(1, (total + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * LIST_PAGE_SIZE
    end = start + LIST_PAGE_SIZE
    rows_html = []
    for i, row in enumerate(items[start:end], start + 1):
        rows_html.append(
            f"<li><strong>{i}. {row.get('name')}</strong><br>"
            f"Зарплата: {row.get('salary', 'N/A')} RUB<br>"
            f"Компания: {row.get('company', 'N/A')}<br>"
            f"Источник: {row.get('source', '?').upper()}<br>"
            f"<a href='{row.get('url', '')}'>Ссылка</a></li>"
        )
    prev_link = f"/list/{token}?page={page-1}" if page > 1 else ""
    next_link = f"/list/{token}?page={page+1}" if page < total_pages else ""
    html = f"""
    <html><head><meta charset="utf-8"><title>Vacancy List</title></head>
    <body>
    <h2>Список вакансий</h2>
    <p>Страница {page} из {total_pages}</p>
    <ol>
    {''.join(rows_html)}
    </ol>
    <div>
        {'<a href="' + prev_link + '">Назад</a>' if prev_link else ''}
        {' | ' if prev_link and next_link else ''}
        {'<a href="' + next_link + '">Вперед</a>' if next_link else ''}
    </div>
    </body></html>
    """
    return web.Response(text=html, content_type="text/html")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/list/{token}", list_page_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    logger.info(f"Web server started on {WEB_HOST}:{WEB_PORT}")
    return runner
