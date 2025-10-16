import os
from openai import AsyncOpenAI

from dotenv import load_dotenv

from api_settings import API_CLIENTS

load_dotenv()


async def make_api_request_with_fallback(
    priority_list,           # Список приоритетов
    messages,                # Сообщения для API
    max_tokens=None,         # Максимум токенов
    temperature=0.1,         # Температура
    task_name="API запрос"  # Название задачи для логов
):
    """
    Пытается выполнить запрос, перебирая клиенты по приоритету
    
    Returns:
        tuple: (response, used_client, used_model) или (None, None, None)
    """
    
    for client_name, model_type in priority_list:
        try:
            client_config = API_CLIENTS[client_name]
            client = client_config["client"]
            model = client_config["models"][model_type]
            
            if not client:
                print(f"⚠️ {task_name}: {client_name} не инициализирован, пропускаем")
                continue
            
            print(f"🔄 {task_name}: Пробуем {client_name} ({model})")
            
            # Проверка здоровья API (опционально)
            # health_ok = await check_api_health(client, model)
            # if not health_ok:
            #     print(f"❌ {task_name}: {client_name} недоступен")
            #     continue
            
            # Выполняем запрос
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            print(f"✅ {task_name}: Успешно через {client_name} ({model})")
            return response, client_name, model
            
        except Exception as e:
            print(f"❌ {task_name}: Ошибка {client_name} - {e}")
            continue
    
    # Все попытки провалились
    print(f"💥 {task_name}: ВСЕ API недоступны!")
    return None, None, None