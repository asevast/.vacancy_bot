def parse_search_options(text: str):
    tokens = text.split()
    opts = {}
    parts = []
    for token in tokens:
        if "=" in token:
            key, value = token.split("=", 1)
            opts[key.strip().lower()] = value.strip()
        else:
            parts.append(token)
    profession = " ".join(parts).strip()
    return profession, opts


def normalize_region_input(raw_region: str) -> str:
    if not raw_region:
        return "Все"
    normalized = raw_region.strip().lower()
    aliases = {
        "moscow": "Москва",
        "москва": "Москва",
        "spb": "СПб",
        "спб": "СПб",
        "saint petersburg": "СПб",
        "st petersburg": "СПб",
        "st. petersburg": "СПб",
        "питер": "СПб",
        "с-пб": "СПб",
        "санкт петербург": "СПб",
        "санкт-петербург": "СПб",
        "nizhny novgorod": "Нижний Новгород",
        "nizhniy novgorod": "Нижний Новгород",
        "нижний новгород": "Нижний Новгород",
        "нижний": "Нижний Новгород",
        "нн": "Нижний Новгород",
        "yekaterinburg": "Екатеринбург",
        "ekaterinburg": "Екатеринбург",
        "екатеринбург": "Екатеринбург",
        "kazan": "Казань",
        "казань": "Казань",
        "all": "Все",
        "any": "Все",
        "все": "Все"
    }
    return aliases.get(normalized, raw_region.strip().title())


def needs_clarification(profession: str) -> bool:
    if not profession:
        return True
    cleaned = profession.strip().lower()
    if len(cleaned) < 3:
        return True
    generic = {
        "dev", "developer", "engineer", "manager", "analyst", "designer",
        "qa", "tester", "marketing", "sales", "it", "admin", "support"
    }
    words = cleaned.split()
    if len(words) == 1 and words[0] in generic:
        return True
    return False


def apply_clarification(base: str, clarification: str) -> str:
    base = (base or "").strip()
    clarification = (clarification or "").strip()
    if not clarification or clarification == "/skip":
        return base
    if base and base.lower() in clarification.lower():
        return clarification
    if len(clarification.split()) >= 2:
        return clarification
    if base:
        return f"{base} {clarification}"
    return clarification
