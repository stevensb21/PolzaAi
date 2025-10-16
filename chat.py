import os
import json
import asyncio
import requests

from ai_request import make_api_request_with_fallback
from api_settings import DATE_CONVERSION_PRIORITY, CERTIFICATE_SEARCH_PRIORITY

from validate import makeOrderformat, validateOrder
from dotenv import load_dotenv
from api import search_employees, addPeople, UpdatePeople


load_dotenv()

chat_history = []


async def main():
    while True:
        order = input("Введите заказ: ")
        if order == "exit":
            break
        
        # Передаем текущее сообщение + всю историю чата
        validation_result = await validateOrder(order, chat_history)
        
        # Пытаемся распарсить JSON ответ
        try:
            if isinstance(validation_result, str):
                # Убираем markdown блоки если есть
                json_str = validation_result.strip()
                if json_str.startswith('```json'):
                    json_str = json_str[7:]  # Убираем ```json
                if json_str.endswith('```'):
                    json_str = json_str[:-3]  # Убираем ```
                json_str = json_str.strip()
                
                order_data = json.loads(json_str)
            else:
                order_data = validation_result
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"📋 Исходный ответ: {validation_result}")
            continue
            
        if order_data.get("error") == "missing_data":
            print(f"❌ Нет данных в заказе: {order_data.get('message')}")
            # Добавляем сообщение пользователя в историю для следующей итерации
            chat_history.append({"role": "user", "content": order})
            continue
        print(f"✅ Данные в заказе проверены: {order_data}")
        # Добавляем сообщение пользователя в историю
        chat_history.append({"role": "user", "content": order})
        chat_history.append({"role": "assistant", "content": str(order_data)})
        order_json = await makeOrderformat(order, chat_history)
        
        # Парсим JSON ответ от makeOrderformat
        try:
            if isinstance(order_json, str):
                # Убираем markdown блоки если есть
                json_str = order_json.strip()
                if json_str.startswith('```json'):
                    json_str = json_str[7:]  # Убираем ```json
                if json_str.endswith('```'):
                    json_str = json_str[:-3]  # Убираем ```
                json_str = json_str.strip()
                
                order_data = json.loads(json_str)
            else:
                order_data = order_json
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON заказа: {e}")
            print(f"📋 Исходный ответ: {order_json}")
            continue
            
        print(f"✅ Формат заказа сформирован: {order_data}")
        
        # Проверяем, существует ли сотрудник
        existing_employee = await search_employees(order_data.get("full_name"))
        
        if existing_employee and isinstance(existing_employee, dict):
            # Обновляем существующего сотрудника
            order_data["id"] = existing_employee.get("id")
            result = await UpdatePeople(order_data)
            print(f"✅ Сотрудник обновлен: {result}")
        else:
            # Добавляем нового сотрудника
            result = await addPeople(order_data)
            print(f"✅ Сотрудник добавлен: {result}")
        
        chat_history.append({"role": "assistant", "content": str(result)})
        print(f"✅ История чата: {chat_history}")
        print(f"🧹 Очищаем историю чата")
        chat_history.clear()
    
if __name__ == "__main__":
    asyncio.run(main())