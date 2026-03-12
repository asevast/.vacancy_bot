import asyncio

from app.config import (
    BOT_TOKEN,
    KILO_AUTO_API_KEY,
    KILO_AUTO_API_URL,
    KILO_AUTO_MODEL,
    SUBSCRIPTION_POLL_SECONDS,
    SJ_API_KEY,
    WEB_HOST,
    WEB_PORT,
    PUBLIC_BASE_URL,
    LIST_PAGE_SIZE,
    LIST_MAX_AGE_HOURS,
    DB_CONFIG,
    HH_API,
    SJ_API,
    HEADERS,
    SJ_HEADERS,
    HABR_API_URL,
    HABR_API_TOKEN,
    AGGREGATOR_API_URL,
    AGGREGATOR_API_TOKEN,
    JOOBLE_API_KEY,
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    ADZUNA_COUNTRY,
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
    LIST_STORE,
    create_list_token,
    get_list_items,
    build_page_keyboard,
    format_vacancy_page,
    build_web_list_link,
    list_page_handler,
    start_web_server
)
from app.analytics import compute_market_stats, format_market_stats
from app.handlers import (
    AREAS,
    SearchForm,
    AIForm,
    SubscribeForm,
    log_callback,
    log_message,
    send_subscription_digest,
    subscription_worker,
    process_profession,
    process_profession_clarification,
    process_salary_from,
    process_salary_to,
    subscribe_command,
    subscribe_profession,
    subscribe_profession_clarification,
    subscribe_salary_from,
    subscribe_salary_to,
    subscribe_region,
    subscriptions_command,
    unsubscribe_command,
    digest_command,
    analyze_callback,
    ai_mode_callback,
    process_ai_prompt,
    clusters_callback,
    page_callback,
    ai_command,
    search_command,
    help_command,
    stats_command,
    cache_command,
    start_handler,
    process_region,
    process_search_confirmation
)
from app.main import main


if __name__ == "__main__":
    asyncio.run(main())
