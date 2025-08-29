import os
import json
import asyncio
import requests
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="https://api.polza.ai/api/v1",
    api_key="ak_XfE3O425uoSp2I3xiLDJXmOX7xGLF3BZ1uXUImXxnpo"
)


BASE_URL = "http://80.87.193.89:8081"
# ==== реальные функции (инструменты) ====

def call_external_api():
    """Забирает JSON сотрудников из твоего API"""
    resp = requests.get(f"{BASE_URL}/api/people", timeout=10)
    resp.raise_for_status()
    return resp.json()

def format_employee(employee: dict) -> str:
    fio = employee.get("full_name", "Неизвестно")
    position = employee.get("position", "Неизвестно")
    all_certs = employee.get("all_certificates", [])

    active = []
    expiring = []
    expired = []
    missing = []

    for c in all_certs:
        assigned = c.get("is_assigned", False)
        data = c.get("assigned_data")
        name = c.get("name", "Неизвестно")

        if assigned and data:
            status = data.get("status")
            date_str = None
            if status == 4:  # Действует
                active.append(f"✅ {name}: Действует до {data.get('assigned_date')}")
            elif status == 3:  # Скоро истекает
                expiring.append(f"⚠ {name}: Истекает {data.get('assigned_date')}")
            elif status == 2:  # Просрочено
                expired.append(f"⭕ {name}: Просрочено с {data.get('assigned_date')}")
            else:
                missing.append(f"❌ {name}")
        else:
            missing.append(f"❌ {name}")

    # Если списки пустые, ставим "отсутствуют" только для expiring
    if not expiring:
        expiring = ["отсутствуют"]

    # Формируем текст
    parts = [
        f"Вот информация по {fio}:",
        f"Должность: {position}",
        "Удостоверения:",
        "Действующие:",
        *active,
        "Скоро просрочатся:",
        *expiring,
        "Просроченные:",
        *expired,
        "Отсутствующие:",
        *missing
    ]

    return "\n".join(parts) 

def create_request(data: dict):
    """Формирует заявку на сотрудника"""
    return {
        "request": "new",
        "employee": data
    }

def send_message(request: dict):
    """Шлёт заявку Ларисе (здесь просто печать для примера)"""
    print("📩 Отправка Ларисе:", json.dumps(request, ensure_ascii=False, indent=2))
    return {"status": "ok", "to": "Лариса"}

# ==== описание инструментов для модели ====

tools = [
    {
        "type": "function",
        "function": {
            "name": "call_external_api",
            "description": "Получает JSON со всеми сотрудниками",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_employee",
            "description": "Форматирует данные сотрудника в красивый текст",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee": {"type": "object", "description": "JSON сотрудника"}
                },
                "required": ["employee"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_request",
            "description": "Создаёт заявку по сотруднику",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "object", "description": "Данные сотрудника и его документы"}
                },
                "required": ["data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Отправляет готовую заявку Ларисе",
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {"type": "object", "description": "Заявка"}
                },
                "required": ["request"]
            }
        }
    }
]

# ==== диспетчер ====

async def run_dispatcher(user_prompt: str):
    response = await client.chat.completions.create(
        model="openai/gpt-4.1-mini",
        messages=[
            {"role": "system", "content": """
                Ты — диспетчер.
                - Если запрос связан с поиском ("покажи", "найди") → вызови call_external_api, выбери подходящих людей, затем вызови format_employee.
                - Если запрос = "создать заявку" → вызови call_external_api (если нужно), затем create_request, затем send_message.
                - Если не понял → уточни у пользователя.
            """},
            {"role": "user", "content": user_prompt}
        ],
        tools=tools
    )

    msg = response.choices[0].message

    # Если модель решила вызвать tool
    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if func_name == "call_external_api":
                result = call_external_api()
            elif func_name == "format_employee":
                result = format_employee(**args)
            elif func_name == "create_request":
                result = create_request(**args)
            elif func_name == "send_message":
                result = send_message(**args)
            else:
                result = {"error": "unknown function"}

            # Отправляем результат обратно
            followup = await client.chat.completions.create(
                model="openai/gpt-4.1-mini",
                messages=[
                    {"role": "user", "content": user_prompt},
                    msg,
                    {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result, ensure_ascii=False)}
                ]
            )
            return followup.choices[0].message.content

    return msg.content

# ==== пример запуска ====

async def main():
    out = await run_dispatcher("Покажи всех Егорова")
    print("🤖 Ответ модели:\n", out)

if __name__ == "__main__":
    asyncio.run(main())