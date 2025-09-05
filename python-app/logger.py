import logging
import os
from datetime import datetime

# Создаем папку для логов если её нет
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Настраиваем форматирование
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Создаем логгер
logger = logging.getLogger('PolzaAI')
logger.setLevel(logging.DEBUG)

# Хендлер для файла
file_handler = logging.FileHandler(
    os.path.join(log_dir, f'polza_ai_{datetime.now().strftime("%Y%m%d")}.log'),
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Хендлер для консоли
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Добавляем хендлеры к логгеру
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def format_long_message(msg, max_length=100):
    """Разбивает длинные сообщения на несколько строк"""
    if len(msg) <= max_length:
        return msg
    
    lines = []
    current_line = ""
    words = msg.split()
    
    for word in words:
        if len(current_line + " " + word) <= max_length:
            current_line += (" " + word) if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return "\n" + "\n".join(f"  {line}" for line in lines)

def log_function_entry(func_name, args=None, kwargs=None):
    """Логирует вход в функцию"""
    msg = f"🚀 Вход в функцию: {func_name}"
    if args:
        msg += f"\n  Аргументы: {args}"
    if kwargs:
        msg += f"\n  Ключевые аргументы: {kwargs}"
    logger.debug(format_long_message(msg))

def log_function_exit(func_name, result=None, error=None):
    """Логирует выход из функции"""
    if error:
        msg = f"❌ Выход из функции {func_name} с ошибкой: {error}"
    else:
        msg = f"✅ Выход из функции {func_name}"
        if result is not None:
            if isinstance(result, str) and len(result) > 100:
                msg += f"\n  Результат: {result[:100]}... (обрезано)"
            else:
                msg += f"\n  Результат: {result}"
    
    logger.debug(format_long_message(msg))

# Функции для удобного логирования
def debug(msg):
    """Логирование отладочной информации"""
    logger.debug(f"🔍 {format_long_message(msg)}")

def info(msg):
    """Логирование информационных сообщений"""
    logger.info(f"ℹ️ {format_long_message(msg)}")

def warning(msg):
    """Логирование предупреждений"""
    logger.warning(f"⚠️ {format_long_message(msg)}")

def error(msg):
    """Логирование ошибок"""
    logger.error(f"❌ {format_long_message(msg)}")

def critical(msg):
    """Логирование критических ошибок"""
    logger.critical(f"🚨 {format_long_message(msg)}")

def success(msg):
    """Логирование успешных операций"""
    logger.info(f"✅ {format_long_message(msg)}")

def ceo(msg):
    """Логирование CEO операций"""
    logger.info(f"🎯 {format_long_message(msg)}")

def search(msg):
    """Логирование поисковых операций"""
    logger.info(f"🔍 {format_long_message(msg)}")

def order(msg):
    """Логирование заказов"""
    logger.info(f"📋 {format_long_message(msg)}")

def bot(msg):
    """Логирование бота"""
    logger.info(f"🤖 {format_long_message(msg)}")

def api(msg):
    """Логирование API операций"""
    logger.info(f"🌐 {format_long_message(msg)}")
