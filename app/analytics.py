from collections import Counter
import pandas as pd

from app.ml import cluster_vacancies


def _normalize_skills(skills_value):
    if skills_value is None:
        return []
    if isinstance(skills_value, list):
        return [s for s in skills_value if s]
    if isinstance(skills_value, str):
        parts = [p.strip() for p in skills_value.replace("|", ",").split(",")]
        return [p for p in parts if p]
    return []


def compute_market_stats(df, top_n_skills=5, top_n_companies=5):
    if df is None or df.empty:
        return None

    stats = {"total": len(df)}

    salary_series = pd.to_numeric(df.get("salary"), errors="coerce").fillna(0)
    salary_series = salary_series[salary_series > 0]
    if not salary_series.empty:
        stats["avg_salary"] = int(salary_series.mean())
        stats["median_salary"] = int(salary_series.median())
        stats["salary_count"] = int(salary_series.count())
    else:
        stats["avg_salary"] = None
        stats["median_salary"] = None
        stats["salary_count"] = 0

    df_clustered = df
    if "cluster" not in df.columns:
        df_clustered = cluster_vacancies(df)
    cluster_counts = df_clustered.get("cluster", pd.Series(dtype=str)).value_counts().to_dict()
    stats["clusters"] = cluster_counts

    skills_counter = Counter()
    if "skills" in df.columns:
        for value in df["skills"]:
            for skill in _normalize_skills(value):
                skills_counter[skill] += 1
    stats["top_skills"] = skills_counter.most_common(top_n_skills)

    companies_counter = Counter()
    if "company" in df.columns:
        for value in df["company"]:
            if value and str(value).strip() and str(value).strip().lower() != "n/a":
                companies_counter[str(value).strip()] += 1
    stats["top_companies"] = companies_counter.most_common(top_n_companies)

    return stats


def format_market_stats(profession, stats):
    if not stats:
        return "Нет данных для аналитики."

    lines = [
        f"Аналитика по запросу: {profession}",
        f"Всего вакансий: {stats.get('total', 0)}"
    ]

    if stats.get("salary_count", 0) > 0:
        lines.append(f"Средняя зарплата: {stats.get('avg_salary')} RUB")
        lines.append(f"Медианная зарплата: {stats.get('median_salary')} RUB")
        lines.append(f"Вакансий с зарплатой: {stats.get('salary_count')}")
    else:
        lines.append("Данные по зарплате отсутствуют.")

    clusters = stats.get("clusters") or {}
    if clusters:
        lines.append("Распределение по уровням:")
        for key, val in clusters.items():
            lines.append(f"- {key}: {val}")

    top_skills = stats.get("top_skills") or []
    if top_skills:
        skills_line = ", ".join([f"{name} ({count})" for name, count in top_skills])
        lines.append(f"Частые навыки: {skills_line}")
    else:
        lines.append("Частые навыки: нет данных.")

    top_companies = stats.get("top_companies") or []
    if top_companies:
        companies_line = ", ".join([f"{name} ({count})" for name, count in top_companies])
        lines.append(f"Топ-компании: {companies_line}")
    else:
        lines.append("Топ-компании: нет данных.")

    return "\n".join(lines)
