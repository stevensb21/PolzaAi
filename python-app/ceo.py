import os
import json
import asyncio
from openai import AsyncOpenAI
from pull_order import connect_dispatcher
from get_jsonAPIai import connect_search_dispatcher 
from dotenv import load_dotenv

load_dotenv()

type_of_request = ""

# Инициализация клиента OpenAI с обработкой ошибок
try:
    client = AsyncOpenAI(
        base_url="https://api.polza.ai/api/v1",
        api_key=os.getenv("POLZA_AI_TOKEN")
    )
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось инициализировать OpenAI клиент: {e}")
    client = None

ceo_chat_history = []

async def ceo_dispatcher(messages):
    """Главный диспетчер, который определяет, какой специализированный диспетчер запустить"""
    try:
        if not client:
            return "❌ Ошибка: OpenAI клиент не инициализирован"
        
        print(f"🎯 CEO анализирует запрос (сообщений: {len(messages)})")
        
        global type_of_request
        global ceo_chat_history
        # Системное сообщение для определения типа запроса
        system_message = {
            "role": "system", 
            "content": """Ты — главный диспетчер (CEO) системы.
            
            У тебя есть 2 специализированных диспетчера:
            
            1. **order_dispatcher** — для заказов удостоверений
               - Запускай когда пользователь хочет ЗАКАЗАТЬ удостоверения
               - Ключевые слова: "заказать", "заказ", "нужно удостоверение", "оформить", "Прошу оформить", "Прошу обучить", "Прошу переобучить"
               - Примеры: "заказать Егорову ЭБ", "нужно удостоверение для Иванова"
            
            2. **search_dispatcher** — для поиска информации о сотрудниках
               - Запускай когда пользователь хочет ПОСМОТРЕТЬ/НАЙТИ информацию
               - Ключевые слова: "показать", "найти", "кто", "информация", "список", "все", "Проверь", "Проверяй"
               - Примеры: "покажи всех", "найди Егорова", "кто работает в отделе"
            
            **ПРАВИЛА:**
            - Анализируй контекст последнего сообщения пользователя
            - В ПЕРВУЮ ОЧЕРЕДЬ проверяй type_of_request если он = "orderclar" то возвращай "order", если он = "searchclar" то возвращай "search" 
            - Если type_of_request = "orderready" то дальше выбирай по контексту запроса
            - Если type_of_request = "searchready" то дальше выбирай по контексту запроса 
            - Если это ЗАКАЗ → возвращай "order"
            - Если это ПОИСК/ПРОСМОТР → возвращай "search"
            - Если неясно → возвращай "search" (по умолчанию)
            
            **ОБЯЗАТЕЛЬНО:** возвращай только одно слово: "order" или "search"
            """
        }
        print(f"🎯\n\n CEO chat_history: {ceo_chat_history}\n\n")
        # Добавляем системное сообщение к истории
        messages_with_system = [system_message] + messages + ceo_chat_history
        print(f"🎯\n\n CEO messages_with_system: {messages_with_system}\n\n")
        print(f"DEBUG: Отправляю {len(messages_with_system)} сообщений в CEO API")
        
        response = await client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=messages_with_system,
            max_tokens=10,
            temperature=0.1
        )
        
        if not response.choices or not response.choices[0].message:
            return "❌ Ошибка: получен пустой ответ от OpenAI API"
        
        decision = response.choices[0].message.content.strip().lower()
        print(f"🎯 CEO решение: {decision}")
        if type_of_request == "orderclar":
            decision = "order"
        elif type_of_request == "searchclar":
            decision = "search"
        print(f"🎯 CEO решение после проверки type_of_request: {decision}, {type_of_request}")
        


        # Определяем, какой диспетчер запустить
        if "order" in decision:
            print("📋 Запускаю order_dispatcher для заказа удостоверений")
            result = await connect_dispatcher(messages, messages_with_system)
            print(f"🎯 CEO результат order_dispatcher: {result.get("type")}")
            type_of_request = result.get("type")
            ceo_chat_history.append({"role": "assistant", "content": result.get("chat_history_order")})
            return result.get("message")
        elif "search" in decision:
            print("🔍 Запускаю search_dispatcher для поиска информации")
            result = await connect_search_dispatcher(messages)
            type_of_request = result.get("type")
            ceo_chat_history.append({"role": "assistant", "content": result.get("message")})
            return result.get("message")
        else:
            print("🔍 По умолчанию запускаю search_dispatcher")
            result = await connect_search_dispatcher(messages)
            type_of_request = result.get("type")
            ceo_chat_history.append({"role": "assistant", "content": result.get("message")})
            return result.get("message")
        
            
    except Exception as e:
        error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА в CEO: {str(e)}"
        print(error_msg)
        return error_msg

# async def main() -> None:
#     """Главная функция для тестирования CEO диспетчера"""
#     print("🎯 CEO диспетчер запущен. Команды: /reset — очистить историю, /exit — выход.")
    
#     chat_history = [
#         {
#             "role": "system",
#             "content": "Ты — пользователь системы. Задавай вопросы о сотрудниках или заказывай удостоверения."
#         }
#     ]
    
#     while True:
#         try:
#             user_input = input("👤 Вы: ").strip()
#             if not user_input:
#                 continue

#             if user_input.lower() in ["/exit", "выход", "quit", "exit"]:
#                 print("До связи!")
#                 break

#             if user_input.lower() in ["/reset", "reset"]:
#                 chat_history = chat_history[:1]
#                 print("История очищена.")
#                 continue

#             # Добавляем сообщение пользователя в историю
#             chat_history.append({"role": "user", "content": user_input})
            
#             # Ограничиваем размер истории
#             if len(chat_history) > 20:
#                 chat_history = [chat_history[0]] + chat_history[-19:]

#             try:
#                 # Отправляем всю историю в CEO диспетчер
#                 ai_text = await ceo_dispatcher(chat_history)
                
#                 # Добавляем ответ ассистента в историю
#                 chat_history.append({"role": "assistant", "content": ai_text})
                
#                 # Выводим ответ
#                 print("🤖 ИИ:\n" + ai_text)
                
#             except Exception as e:
#                 error_msg = f"❌ Ошибка при обработке запроса: {str(e)}"
#                 print(error_msg)
#                 chat_history.append({"role": "assistant", "content": error_msg})
                
#         except KeyboardInterrupt:
#             print("\n\n👋 Прерывание пользователем. До свидания!")
#             break
#         except Exception as e:
#             print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в главном цикле: {str(e)}")
#             continue

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except Exception as e:
#         print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при запуске: {str(e)}")

