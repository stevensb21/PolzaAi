import os
import json
import asyncio
import requests
from openai import AsyncOpenAI
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from ai_request import make_api_request_with_fallback
from validate import convert_date

load_dotenv()

async def addPeople(employee):
    print(f"🔍 Добавляем пользователя {employee.get('full_name', ''), employee.get('position', ''), employee.get('phone', ''), employee.get('snils', ''), employee.get('inn', ''), employee.get('birth_date', ''), employee.get( '@'+'photo', '')}")
    data = {
        "full_name": employee.get("full_name", ""),
        "position": employee.get("position", ""),
        "phone": employee.get("phone", ""),
        "snils": employee.get("snils", ""),
        "inn": employee.get("inn", ""),
        "birth_date": await convert_date(employee.get("birth_date", "")) if employee.get("birth_date", "").strip() else "",
        "status": "В ожидании",
        "photo": employee.get( '@'+'photo', "")
    }
    try:
        response = requests.post(
            os.getenv("BASE_URL") + "/api/people",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "PolzaAI-Bot/1.0",
                "Authorization": f'Bearer {os.getenv("API_TOKEN")}'
            },
            json=data,
            timeout=30,
                proxies={"http": None, "https": None}
        )
    except Exception as e:
        print(f"❌ Ошибка при добавлении пользователя {employee.get('full_name', '')}: {e}")
        return None

    if response.status_code == 200 or response.status_code == 201:
        print(f"✅ Пользователь {employee.get('full_name', '')} успешно добавлен")
        print(f"📋 Ответ сервера: {response.text}")
        return response.json()
    else:
        print(f"❌ Ошибка при добавлении пользователя {employee.get('full_name', '')}: {response.status_code} {response.text}")
        return None

async def UpdatePeople(employee):
    print(f"🔍 Обновляем пользователя {employee.get('full_name', '')}")
    data = {
        "full_name": employee.get("full_name", ""),
        "position": employee.get("position", ""),
        "phone": employee.get("phone", ""),
        "snils": employee.get("snils", ""),
        "inn": employee.get("inn", ""),
        "birth_date": await convert_date(employee.get("birth_date", "")),
        "status": "В ожидании",
        "photo": employee.get( '@'+'photo', "")
    }
    url = os.getenv("BASE_URL") + "/api/people/" + str(employee.get("id", ""))
    print(f"🌐 URL для обновления: {url}")
    try:
        response = requests.put(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "PolzaAI-Bot/1.0",
                "Authorization": f'Bearer {os.getenv("API_TOKEN")}'
            },
            json=data,
            timeout=30,
                proxies={"http": None, "https": None}
        )
    except Exception as e:
        print(f"❌ Ошибка при обновлении пользователя {employee.get('full_name', '')}: {e}")
        return None

    if response.status_code == 200 or response.status_code == 201:
        print(f"✅ Пользователь {employee.get('full_name', '')} успешно обновлен")
        return response.json()
    else:
        print(f"❌ Ошибка при обновлении пользователя {employee.get('full_name', '')}: {response.status_code} {response.text}")
        return None

async def getPeople(id):
    try:
        response = requests.get(
            os.getenv("BASE_URL") + "/api/people/" + str(id),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "PolzaAI-Bot/1.0",
                "Authorization": f'Bearer {os.getenv("API_TOKEN")}'
            },
            timeout=30,
                proxies={"http": None, "https": None}
        )
    except Exception as e:
        print(f"❌ Ошибка при получении пользователя {id}: {e}")
        return None
    
    if response.status_code == 200:
        print(f"✅ Пользователь {id} успешно получен")
        return response.json()
    else:
        print(f"❌ Ошибка при получении пользователя {id}: {response.status_code} {response.text}")
        return None

async def allPeople():

    """Вызывает внешний API с надежной обработкой ошибок"""
    
    try:
        api_token = os.getenv("API_TOKEN")
        
        if not api_token:
            return {
                "error": "API_TOKEN не найден",
                "details": "Проверьте файл .env и переменную API_TOKEN"
            }
        
        headers = {
            'User-Agent': 'PolzaAI-Bot/1.0',
            'Authorization': f'Bearer {api_token}'
        }
        

        resp = requests.get(
            f"{os.getenv('BASE_URL')}/api/people/compact?limit=1000",  # Устанавливаем лимит 1000 для получения всех людей
            timeout=60,  # Увеличиваем таймаут для больших запросов
            proxies={"http": None, "https": None},
            headers=headers
        )
        
    # Проверяем, сколько записей получили
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and 'data' in data:
                print(f"Получено {len(data['data'])} записей")
                return data['data']
            else:
                return {
                    "error": "Неверный формат данных",
                    "details": f"URL: {os.getenv('BASE_URL')}/api/people/compact?limit=1000",
                    "response_text": resp.text
                }
        else:
            return {
                "error": f"API вернул статус {resp.status_code}",
                "details": f"URL: {os.getenv('BASE_URL')}/api/people/compact?limit=1000",
                "response_text": resp.text
            }
    except Exception as e:
        print(f"❌ Ошибка при получении всех пользователей: {e}")
        return None


import re

def normalize_text(text):
    """Нормализует текст для поиска: убирает ВСЕ пробелы, приводит к нижнему регистру"""
    if not text:
        return ""
    # Убираем ВСЕ пробелы, переносы строк, табы
    normalized = re.sub(r'\s+', '', str(text).strip())
    # Приводим к нижнему регистру
    return normalized.lower()

def fuzzy_search(query, target_text):
    """Нечеткий поиск с нормализацией текста"""
    if not query or not target_text:
        return False
    
    # Нормализуем оба текста
    norm_query = normalize_text(query)
    norm_target = normalize_text(target_text)
    
    # Точное совпадение
    if norm_query == norm_target:
        return True
    
    # Поиск подстроки
    if norm_query in norm_target:
        return True
    
    return False

async def get_employee_certificates(employee_id):
    """
    Получает сертификаты сотрудника
    
    Args:
        employee_id: ID сотрудника
    
    Returns:
        list: Список сертификатов или None
    """
    try:
        api_token = os.getenv("API_TOKEN")
        
        if not api_token:
            print("❌ API_TOKEN не найден")
            return None
        
        headers = {
            'User-Agent': 'PolzaAI-Bot/1.0',
            'Authorization': f'Bearer {api_token}'
        }
        
        resp = requests.get(
            f"{os.getenv('BASE_URL')}/api/people/{employee_id}",
            timeout=30,
            proxies={"http": None, "https": None},
            headers=headers
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and 'data' in data:
                employee_data = data['data']
                print(f"🔍 Структура данных сотрудника: {list(employee_data.keys())}")
                certificates = employee_data.get('all_certificates', [])
                print(f"✅ Получено {len(certificates)} сертификатов для сотрудника {employee_id}")
                
                # Проверяем другие возможные поля для сертификатов
                if not certificates:
                    print(f"🔍 Проверяем другие поля для сертификатов...")
                    for key in employee_data.keys():
                        if 'certificate' in key.lower() or 'удостоверение' in key.lower():
                            print(f"🔍 Найдено поле {key}: {employee_data[key]}")
                
                return certificates
            else:
                print(f"❌ Неверный формат данных для сотрудника {employee_id}")
                print(f"🔍 Структура данных: {data}")
                return []
        else:
            print(f"❌ Ошибка API при получении сертификатов: {resp.status_code}")
            print(f"🔍 Ответ сервера: {resp.text}")
            return []
            
    except Exception as e:
        print(f"❌ Ошибка при получении сертификатов: {e}")
        return []

async def search_employees(query):
    """
    Улучшенный поиск сотрудников с нормализацией текста
    
    Args:
        query: Поисковый запрос (ФИО, часть имени и т.д.)
    
    Returns:
        dict: Найденный сотрудник или None
    """
    print(f"🔍 search_employees вызвана с запросом: {query}")
    if not query or not query.strip():
        print("❌ Пустой запрос")
        return None
    
    try:
        print(f"🔍 Получаем всех сотрудников...")
        employees = await allPeople()
        print(f"🔍 Получено {len(employees) if employees else 0} сотрудников")
       
        
        if not employees or isinstance(employees, dict) and 'error' in employees:
            print(f"❌ Ошибка получения данных: {employees}")
            return None
      
        # Ищем точное совпадение
        print(f"🔍 Начинаем поиск среди {len(employees)} сотрудников")
        for i, employee in enumerate(employees):
            if not isinstance(employee, dict) or 'full_name' not in employee:
                continue
            
            employee_name = employee.get('full_name', '')
            
            if fuzzy_search(query, employee_name):
                print(f"✅ Найден сотрудник: {employee_name}")
                
                # Получаем сертификаты сотрудника
                employee_id = employee.get('id')
                certificates = []
                if employee_id:
                    print(f"🔍 Получаем сертификаты для ID: {employee_id}")
                    certificates = await get_employee_certificates(employee_id)
                    print(f"🔍 Получено сертификатов: {len(certificates)}")
                
                # Возвращаем основные поля + сертификаты
                filtered_employee = {
                    'id': employee.get('id'),
                    'full_name': employee.get('full_name'),
                    'position': employee.get('position'),
                    'phone': employee.get('phone'),
                    'status': employee.get('status', 'Не указан'),
                    'snils': employee.get('snils'),
                    'inn': employee.get('inn'),
                    'birth_date': employee.get('birth_date'),
                    'photo': employee.get('photo'),
                    'certificates': certificates
                }
                return filtered_employee
        
       
        
    except Exception as e:
        print(f"❌ Ошибка при поиске сотрудников: {e}")
        return None


async def main():
    employees = await search_employees("John Doe")
    print(employees)

# async def main():
#     employee = {
#         "full_name": "John Doe",
#         "position": "Developer",
#         "phone": "1234567890",
#         "snils": "1234567890",
#         "inn": "1234567890",
#         "birth_date": "2000-01-01"
#     }
#     result = await addPeople(employee)
#     print(result)

#     # Проверяем, что пользователь был успешно добавлен
#     if result and isinstance(result, dict) and result.get("success") and "data" in result:
#         user_id = result["data"].get("id")
#         print(f"📋 ID добавленного пользователя: {user_id}")
        
#         # Получаем данные пользователя для обновления
#         employee = await getPeople(user_id)
#         print(employee)
#         if employee and isinstance(employee, dict) and employee.get("success") and "data" in employee:
#             # Извлекаем данные пользователя из ответа
#             user_data = employee["data"]
#             user_data["position"] = "Engineer"
#             update_result = await UpdatePeople(user_data)
#             print(update_result)
#         else:
#             print("❌ Не удалось получить пользователя для обновления")

#         # Проверяем обновленные данные
#         employee = await getPeople(user_id)
#         print(employee)
#     else:
#         print("❌ Пользователь не был добавлен или не получен ID")

if __name__ == "__main__":
    asyncio.run(main())