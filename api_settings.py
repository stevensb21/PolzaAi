import os
from openai import AsyncOpenAI

from dotenv import load_dotenv


load_dotenv()

# Инициализация клиентов
print(f"🔍 POLZA_AI_TOKEN: {os.getenv('POLZA_AI_TOKEN')[:10]}..." if os.getenv('POLZA_AI_TOKEN') else "❌ POLZA_AI_TOKEN не найден")

try:
    client_polza = AsyncOpenAI(
        base_url="https://api.polza.ai/api/v1",
        api_key=os.getenv("POLZA_AI_TOKEN")
    )
except Exception as e:
    print(f"❌ Ошибка инициализации Polza клиента: {e}")
    client_polza = None

try:
    client_vsegpt = AsyncOpenAI(
        base_url="https://api.vsegpt.ru/v1",
        api_key=os.getenv("VSEGPT_API_KEY")
    )
except Exception as e:
    print(f"❌ Ошибка инициализации Vsegpt клиента: {e}")
    client_vsegpt = None

try:
    client_proxyapi = AsyncOpenAI(
        base_url="https://api.proxyapi.ru/openai/v1",
        api_key=os.getenv("PROXYAPI_API_KEY")
    )
except Exception as e:
    print(f"❌ Ошибка инициализации Proxyapi клиента: {e}")
    client_proxyapi = None


# Модели из переменных окружения
OPENAI_MODEL_POLZA_4_1 = os.getenv("OPENAI_MODEL_POLZA_4_1", "openai/gpt-4.1-mini")    
GEMINI_MODEL_POLZA_2_0 = os.getenv("GEMINI_MODEL_POLZA_2_0", "google/gemini-2.0-flash-lite-001")
OPENAI_MODEL_VSEGPT = os.getenv("OPENAI_MODEL_VSEGPT", "openai/gpt-4o-mini")
GEMINI_MODEL_VSEGPT = os.getenv("GEMINI_MODEL_VSEGPT", "google/gemini-2.0-flash")
OPENAI_MODEL_PROXYAPI = os.getenv("OPENAI_MODEL_PROXYAPI", "gpt-4o-mini")
GEMINI_MODEL_PROXYAPI = os.getenv("GEMINI_MODEL_PROXYAPI", "gemini-2.0-flash")

# Конфигурация клиентов и моделей
API_CLIENTS = {
    "polza": {
        "client": client_polza,
        "base_url": "https://api.polza.ai/api/v1",
        "token_env": "POLZA_AI_TOKEN",
        "models": {
            "openai": OPENAI_MODEL_POLZA_4_1,
            "gemini": GEMINI_MODEL_POLZA_2_0
        }
    },
    "vsegpt": {
        "client": client_vsegpt,
        "base_url": "https://api.vsegpt.ru/v1",
        "token_env": "VSEGPT_API_KEY",
        "models": {
            "openai": OPENAI_MODEL_VSEGPT,
            "gemini": GEMINI_MODEL_VSEGPT
        }
    },
    "proxyapi": {
        "client": client_proxyapi,
        "base_url": "https://api.proxyapi.ru/openai/v1",
        "token_env": "PROXYAPI_API_KEY",
        "models": {
            "openai": OPENAI_MODEL_PROXYAPI,
            "gemini": GEMINI_MODEL_PROXYAPI
        }
    }
}



# Приоритеты для check_if_protocol (быстрая проверка)
PRIORITY_MODEL = [
    ("polza", "openai"),      # Быстрая и дешевая
    ("proxyapi", "openai"), # Запасной вариант 1
    ("vsegpt", "openai"),     # Запасной вариант 2
    ("polza", "gemini"),      # Если openai не работают
    ("proxyapi", "gemini"),
    ("vsegpt", "gemini")
]

