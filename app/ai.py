import asyncio
import aiohttp

from app.config import KILO_AUTO_API_KEY, KILO_AUTO_API_URL, KILO_AUTO_MODEL, logger


async def ask_kilo_auto(prompt: str) -> str:
    """Отправка запроса к Kilo Auto AI"""
    if not KILO_AUTO_API_KEY:
        return "ERROR: KILO_AUTO_API_KEY not configured"
    
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
            resp = await session.post(
                url,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            )
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
