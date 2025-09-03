import os
import json
import asyncio
import requests
from openai import AsyncOpenAI

# Инициализация клиента (как в проекте)
client = AsyncOpenAI(
    base_url="https://api.polza.ai/api/v1",
    api_key="ak_XfE3O425uoSp2I3xiLDJXmOX7xGLF3BZ1uXUImXxnpo"
)

# Базовый контекст — сюда можно добавлять справочные данные/переменные
CONTEXT = {
    "users": {
        "лариса": {
            "telegram_id": "8316311496",
            "alias": ["лариса", "лариса из отдела", "лариса менеджер"],
        }
    },
    "endpoints": {
        "people_list": "http://80.87.193.89:8081/api/people",
        "people_data": "http://80.87.193.89:8001/data"
    },
    "instructions": [
        "Отвечай по-русски.",
        "Помни контекст диалога и ранее упомянутые факты.",
        "Если собеседник говорит о Ларисе, знай, что это telegram-пользователь с id:8316311496.",
        "Если просит что-то повторить или уточнить — делай это кратко и по делу.",
    ]
}

# История чата — для сохранения контекста
chat_history = [
    {
        "role": "system",
        "content": (
            "Ты — вежливый и внимательный ассистент. Общайся как человек, "+
            "держи краткий и точный стиль. У тебя есть вспомогательный контекст: "
            + json.dumps(CONTEXT, ensure_ascii=False)
        ),
    }
]

async def send_to_ai(messages: list) -> str:
    """Отправка истории сообщений в модель и возврат ответа ассистента."""
    response = await client.chat.completions.create(
        model="openai/gpt-4.1-mini",
        messages=messages,
    )
    return response.choices[0].message.content or ""

async def main() -> None:
    print("Контекстный чат запущен. Команды: /reset — очистить историю, /exit — выход.")
    while True:
        user_input = input("👤 Вы: ").strip()
        if not user_input:
            continue

        if user_input.lower() in ["/exit", "выход", "quit", "exit"]:
            print("До связи!")
            break

        if user_input.lower() in ["/reset", "reset"]:
            # Сброс истории, но сохраняем системный контекст
             
            global chat_history
            chat_history = chat_history[:1]
            print("История очищена.")
            continue

        # Добавляем сообщение пользователя
        chat_history.append({"role": "user", "content": user_input})

        # Ограничиваем длину истории, чтобы не раздувать запрос
        if len(chat_history) > 20:
            # сохраняем системное сообщение и последние 19 сообщений
            chat_history[:] = [chat_history[0]] + chat_history[-19:]

        try:
            # Запрашиваем ответ модели
            ai_text = await send_to_ai(chat_history)
            # Добавляем ответ ассистента в историю
            chat_history.append({"role": "assistant", "content": ai_text})
            print("🤖 ИИ:\n" + ai_text)
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())

