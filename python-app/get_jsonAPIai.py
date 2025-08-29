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


async def sort_employee(employee):
    """Выбирает сотрудников из JSON"""
    user_prompt = f"Выбери сотрудников из JSON по фильтру: {employee}"
    json_employee = call_external_api()
    response = await client.chat.completions.create(
        model="openai/gpt-4.1",
        messages=[
            {"role": "system", "content": """
                Ты — выбиратель сотрудников.
                -вызови call_external_api
                -выбери сотрудников или сотрудника из JSON по фильтру, сотрудников по фильтру может быть несколько или один
                - если сотрудников несколько, верни список сотрудников, если один, верни объект сотрудника
                -верни полный JSON сотрудников или сотрудника, ничего не обрезай, если нет сотрудников, верни пустой JSON с сообщением "нет сотрудников"
            """},
            {"role": "user", "content": employee},
            {"role": "assistant", "content": json.dumps(json_employee)}
        ],
        tools=tools
    )
    return response.choices[0].message.content

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
            "name": "sort_employee",
            "description": "Выбирает сотрудников из JSON",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee": {"type": "string", "description": "Фильтр для выбора сотрудников"}
                },
                "required": ["employee"]
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
                -вызови sort_employee
                
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
            elif func_name == "sort_employee":
                result = await sort_employee(args["employee"])
            else:
                result = {"error": "unknown function"}

            
            return result

    return msg.content

# ==== пример запуска ====

async def main():
    out = await run_dispatcher("Покажи всех прорабов")
    print("🤖 Ответ модели:\n", out)

if __name__ == "__main__":
    asyncio.run(main())