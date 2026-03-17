import time
import requests
import pandas as pd
from requests.exceptions import RequestException, Timeout, HTTPError, SSLError

from app.config import (
    HH_API,
    SJ_API,
    HEADERS,
    SJ_HEADERS,
    SJ_API_KEY,
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


def parse_hh_vacancies(
    text,
    area=113,
    salary_from=None,
    salary_to=None,
    count=50,
    region_label=None,
    experience=None,
    employment=None,
    only_with_salary=None,
    schedule=None,
    professional_role=None,
    search_field=None,
    period=None,
    currency=None,
    label=None,
    order_by=None,
    page=None
):
    """HH.ru API"""
    logger.info(f"HH.ru API request: text='{text}', area={area}")
    
    params = {"text": text, "area": area, "per_page": min(count, 100)}
    if salary_from: params["salary_from"] = salary_from
    if salary_to: params["salary_to"] = salary_to
    if experience: params["experience"] = experience
    if employment: params["employment"] = employment
    if only_with_salary: params["only_with_salary"] = 1
    if schedule: params["schedule"] = schedule
    if professional_role: params["professional_role"] = professional_role
    if search_field: params["search_field"] = search_field
    if period: params["period"] = period
    if currency: params["currency"] = currency
    if label: params["label"] = label
    if order_by: params["order_by"] = order_by
    if page is not None: params["page"] = page
    
    try:
        resp = None
        last_err = None
        for attempt in range(3):
            try:
                resp = requests.get(HH_API, params=params, headers=HEADERS, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                break
            except (SSLError, Timeout, RequestException) as e:
                last_err = e
                logger.warning(f"HH.ru retry {attempt + 1}/3 | {e}")
                if attempt < 2:
                    time.sleep(1 + attempt)
        else:
            raise last_err
        
        if "items" not in data:
            logger.warning(f"HH.ru response missing 'items': {data.get('errors', 'Unknown error')}")
            return pd.DataFrame()
        
        vacancies = []
        for vac in data.get("items", []):
            salary = vac.get("salary")
            salary_rub = 0
            
            if salary and isinstance(salary, dict):
                salary_currency = salary.get("currency")
                if salary_currency == "RUR":
                    from_val = salary.get("from")
                    to_val = salary.get("to")
                    if from_val and to_val:
                        salary_rub = (from_val + to_val) // 2
                    elif from_val:
                        salary_rub = from_val
                    elif to_val:
                        salary_rub = to_val
            
            snippet = vac.get("snippet") or {}
            snippet_req = snippet.get("requirement") or ""
            snippet_resp = snippet.get("responsibility") or ""
            skills = [s["name"] for s in vac.get("key_skills", [])]
            desc = str(snippet_req) + " " + str(snippet_resp)
            
            employer = vac.get("employer")
            company = employer.get("name") if employer else "Unknown"
            
            experience = "unknown"
            exp_data = vac.get("experience")
            if exp_data and isinstance(exp_data, dict):
                experience = exp_data.get("id", "unknown")
            
            vacancies.append({
                "source": "hh",
                "external_id": vac["id"],
                "name": vac["name"],
                "employer": employer or {},
                "company": company,
                "salary": salary_rub,
                "description": desc,
                "skills": skills,
                "experience": experience,
                "url": vac["alternate_url"],
                "region": region_label
            })
        return pd.DataFrame(vacancies)
    except HTTPError as e:
        logger.error(f"HH.ru HTTP ERROR | {e}")
        raise
    except Timeout:
        logger.error(f"HH.ru TIMEOUT | text='{text}'")
        raise TimeoutError("Timeout when requesting HH.ru. Try again later.")
    except SSLError as e:
        logger.error(f"HH.ru SSL ERROR | {e}")
        raise ConnectionError(f"SSL error with HH.ru: {e}")
    except RequestException as e:
        logger.error(f"HH.ru ERROR | {e}")
        raise ConnectionError(f"Connection error with HH.ru: {e}")
    except Exception as e:
        logger.error(f"HH.ru UNEXPECTED | {e}")
        raise


def parse_superjob_vacancies(text, town_id=4, payment_from=None, payment_to=None, count=50, region_label=None):
    """SuperJob API (без авторизации)"""
    if not SJ_API_KEY:
        logger.warning("SuperJob API key not configured; skipping SuperJob requests.")
        return pd.DataFrame()
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
        resp = None
        last_err = None
        for attempt in range(3):
            try:
                resp = requests.get(SJ_API, params=params, headers=SJ_HEADERS, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                break
            except HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                if status in {429, 500, 502, 503, 504} and attempt < 2:
                    logger.warning(f"SuperJob retry {attempt + 1}/3 | HTTP {status}")
                    time.sleep(1 + attempt)
                    continue
                raise
            except (SSLError, Timeout, RequestException) as e:
                last_err = e
                logger.warning(f"SuperJob retry {attempt + 1}/3 | {e}")
                if attempt < 2:
                    time.sleep(1 + attempt)
        else:
            if isinstance(last_err, Timeout):
                raise TimeoutError("Timeout when requesting SuperJob. Try again later.")
            raise ConnectionError(f"Connection error with SuperJob: {last_err}")
        
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
                "url": f"https://www.superjob.ru/vakansii/{vac['id']}.html",
                "region": region_label
            })
        return pd.DataFrame(vacancies)
    except HTTPError as e:
        logger.error(f"SuperJob HTTP ERROR | {e}")
        raise


def parse_habr_vacancies(text, count=50, region_label=None):
    """Habr Career API (если доступен токен/публичный доступ)."""
    if not HABR_API_URL:
        return pd.DataFrame()

    headers = {"User-Agent": "VacancyBotPro/1.0"}
    if HABR_API_TOKEN:
        headers["Authorization"] = f"Bearer {HABR_API_TOKEN}"

    params = {
        "q": text,
        "query": text,
        "limit": min(count, 100)
    }

    try:
        resp = requests.get(HABR_API_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("vacancies") or data.get("items") or data.get("results") or []
        vacancies = []
        for vac in items:
            salary = vac.get("salary") or {}
            salary_from = salary.get("from") or salary.get("min") or 0
            salary_to = salary.get("to") or salary.get("max") or 0
            salary_avg = 0
            if salary_from and salary_to:
                salary_avg = (salary_from + salary_to) // 2
            elif salary_from:
                salary_avg = salary_from
            elif salary_to:
                salary_avg = salary_to

            company = ""
            if isinstance(vac.get("company"), dict):
                company = vac.get("company", {}).get("name", "")
            company = company or vac.get("company_name", "N/A")

            vacancies.append({
                "source": "habr",
                "external_id": str(vac.get("id") or vac.get("vacancy_id") or ""),
                "name": vac.get("title") or vac.get("name") or vac.get("position") or "",
                "company": company,
                "salary": salary_avg,
                "description": vac.get("description") or vac.get("body") or "",
                "skills": vac.get("skills") or vac.get("tags") or [],
                "experience": vac.get("experience") or vac.get("level") or "unknown",
                "url": vac.get("url") or vac.get("link") or "",
                "region": region_label
            })
        return pd.DataFrame(vacancies)
    except HTTPError as e:
        logger.error(f"Habr HTTP ERROR | {e}")
        raise
    except Timeout:
        logger.error(f"Habr TIMEOUT | text='{text}'")
        raise TimeoutError("Timeout when requesting Habr Career. Try again later.")
    except SSLError as e:
        logger.error(f"Habr SSL ERROR | {e}")
        raise ConnectionError(f"SSL error with Habr Career: {e}")
    except RequestException as e:
        logger.error(f"Habr ERROR | {e}")
        raise ConnectionError(f"Connection error with Habr Career: {e}")
    except Exception as e:
        logger.error(f"Habr UNEXPECTED | {e}")
        raise


def parse_aggregator_vacancies(text, count=50, region_label=None):
    """Generic aggregator API integration (configurable)."""
    if not AGGREGATOR_API_URL:
        return pd.DataFrame()

    headers = {"User-Agent": "VacancyBotPro/1.0"}
    if AGGREGATOR_API_TOKEN:
        headers["Authorization"] = f"Bearer {AGGREGATOR_API_TOKEN}"

    params = {
        "query": text,
        "q": text,
        "limit": min(count, 100)
    }

    try:
        resp = requests.get(AGGREGATOR_API_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items") or data.get("vacancies") or data.get("results") or []
        vacancies = []
        for vac in items:
            salary_from = vac.get("salary_from") or vac.get("salaryMin") or 0
            salary_to = vac.get("salary_to") or vac.get("salaryMax") or 0
            salary_avg = 0
            if salary_from and salary_to:
                salary_avg = (salary_from + salary_to) // 2
            elif salary_from:
                salary_avg = salary_from
            elif salary_to:
                salary_avg = salary_to

            vacancies.append({
                "source": "agg",
                "external_id": str(vac.get("id") or vac.get("external_id") or ""),
                "name": vac.get("title") or vac.get("name") or "",
                "company": vac.get("company") or vac.get("employer") or "N/A",
                "salary": salary_avg,
                "description": vac.get("description") or "",
                "skills": vac.get("skills") or [],
                "experience": vac.get("experience") or "unknown",
                "url": vac.get("url") or vac.get("link") or "",
                "region": region_label
            })
        return pd.DataFrame(vacancies)
    except HTTPError as e:
        logger.error(f"Aggregator HTTP ERROR | {e}")
        raise
    except Timeout:
        logger.error(f"Aggregator TIMEOUT | text='{text}'")
        raise TimeoutError("Timeout when requesting aggregator. Try again later.")
    except SSLError as e:
        logger.error(f"Aggregator SSL ERROR | {e}")
        raise ConnectionError(f"SSL error with aggregator: {e}")
    except RequestException as e:
        logger.error(f"Aggregator ERROR | {e}")
        raise ConnectionError(f"Connection error with aggregator: {e}")
    except Exception as e:
        logger.error(f"Aggregator UNEXPECTED | {e}")
        raise


def parse_jooble_vacancies(text, count=50, region_label=None):
    """Jooble API (requires JOOBLE_API_KEY)."""
    if not JOOBLE_API_KEY:
        return pd.DataFrame()

    url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
    payload = {
        "keywords": text,
        "location": region_label if region_label and region_label != "Все" else "",
        "page": 1,
        "resultOnPage": min(count, 100)
    }
    try:
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("jobs") or data.get("items") or []
        vacancies = []
        for vac in items:
            salary = vac.get("salary") or ""
            salary_avg = 0
            if isinstance(salary, (int, float)):
                salary_avg = int(salary)
            vacancies.append({
                "source": "jooble",
                "external_id": str(vac.get("id") or vac.get("jobkey") or ""),
                "name": vac.get("title") or vac.get("name") or "",
                "company": vac.get("company") or "N/A",
                "salary": salary_avg,
                "description": vac.get("snippet") or vac.get("description") or "",
                "skills": vac.get("skills") or [],
                "experience": vac.get("experience") or "unknown",
                "url": vac.get("link") or vac.get("url") or "",
                "region": region_label
            })
        return pd.DataFrame(vacancies)
    except HTTPError as e:
        logger.error(f"Jooble HTTP ERROR | {e}")
        raise
    except Timeout:
        logger.error(f"Jooble TIMEOUT | text='{text}'")
        raise TimeoutError("Timeout when requesting Jooble. Try again later.")
    except SSLError as e:
        logger.error(f"Jooble SSL ERROR | {e}")
        raise ConnectionError(f"SSL error with Jooble: {e}")
    except RequestException as e:
        logger.error(f"Jooble ERROR | {e}")
        raise ConnectionError(f"Connection error with Jooble: {e}")
    except Exception as e:
        logger.error(f"Jooble UNEXPECTED | {e}")
        raise


def parse_adzuna_vacancies(text, count=50, region_label=None):
    """Adzuna API (requires ADZUNA_APP_ID/ADZUNA_APP_KEY)."""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return pd.DataFrame()

    page = 1
    url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/{page}"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": text,
        "where": region_label if region_label and region_label != "Все" else "",
        "results_per_page": min(count, 50)
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("results") or data.get("items") or []
        vacancies = []
        for vac in items:
            salary_min = vac.get("salary_min") or 0
            salary_max = vac.get("salary_max") or 0
            salary_avg = 0
            if salary_min and salary_max:
                salary_avg = int((salary_min + salary_max) // 2)
            elif salary_min:
                salary_avg = int(salary_min)
            elif salary_max:
                salary_avg = int(salary_max)

            company = ""
            if isinstance(vac.get("company"), dict):
                company = vac.get("company", {}).get("display_name", "")
            company = company or vac.get("company", "N/A")

            vacancies.append({
                "source": "adzuna",
                "external_id": str(vac.get("id") or ""),
                "name": vac.get("title") or "",
                "company": company,
                "salary": salary_avg,
                "description": vac.get("description") or "",
                "skills": vac.get("skills") or [],
                "experience": vac.get("experience") or "unknown",
                "url": vac.get("redirect_url") or vac.get("url") or "",
                "region": region_label
            })
        return pd.DataFrame(vacancies)
    except HTTPError as e:
        logger.error(f"Adzuna HTTP ERROR | {e}")
        raise
    except Timeout:
        logger.error(f"Adzuna TIMEOUT | text='{text}'")
        raise TimeoutError("Timeout when requesting Adzuna. Try again later.")
    except SSLError as e:
        logger.error(f"Adzuna SSL ERROR | {e}")
        raise ConnectionError(f"SSL error with Adzuna: {e}")
    except RequestException as e:
        logger.error(f"Adzuna ERROR | {e}")
        raise ConnectionError(f"Connection error with Adzuna: {e}")
    except Exception as e:
        logger.error(f"Adzuna UNEXPECTED | {e}")
        raise
