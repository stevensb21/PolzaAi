# 🐳 Docker развертывание PolzaAI Bot

Этот документ описывает, как развернуть PolzaAI Bot с помощью Docker.

## 📋 Предварительные требования

- Docker
- Docker Compose
- Git

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd PolzaAi/python-app

# Создайте .env файл с вашими токенами
cp .env.example .env
# Отредактируйте .env файл, добавив ваши токены
```

### 2. Запуск

```bash
# Сделайте скрипт исполняемым
chmod +x docker-scripts.sh

# Соберите и запустите контейнеры
./docker-scripts.sh build
./docker-scripts.sh up
```

### 3. Проверка статуса

```bash
# Проверьте статус контейнеров
./docker-scripts.sh status

# Посмотрите логи
./docker-scripts.sh logs
```

## 📁 Структура проекта

```
python-app/
├── Dockerfile              # Docker образ
├── docker-compose.yml      # Docker Compose конфигурация
├── .dockerignore           # Игнорируемые файлы
├── docker-scripts.sh       # Скрипт управления
├── .env                    # Переменные окружения
├── requirements.txt        # Python зависимости
├── bot.py                  # Основной файл бота
├── logs/                   # Логи (монтируются как volume)
└── images/                 # Изображения (монтируются как volume)
```

## 🔧 Управление контейнерами

### Основные команды

```bash
# Сборка образа
./docker-scripts.sh build

# Запуск контейнеров
./docker-scripts.sh up

# Остановка контейнеров
./docker-scripts.sh down

# Перезапуск
./docker-scripts.sh restart

# Просмотр логов
./docker-scripts.sh logs

# Статус контейнеров
./docker-scripts.sh status

# Подключение к контейнеру
./docker-scripts.sh shell

# Полная пересборка
./docker-scripts.sh rebuild

# Обновление и перезапуск
./docker-scripts.sh update
```

### Прямые команды Docker Compose

```bash
# Запуск в фоновом режиме
docker-compose up -d

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f polza-ai-bot

# Пересборка
docker-compose build --no-cache
```

## 🔐 Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.polza.ai/api/v1
```

## 📊 Мониторинг

### Health Checks

Контейнеры имеют встроенные health checks:

- **Bot**: Проверяет доступность Telegram API
- **Redis**: Проверяет ping команду

### Логи

Логи сохраняются в директории `./logs/` и доступны через:

```bash
# Логи бота
./docker-scripts.sh logs

# Логи Redis
./docker-scripts.sh logs-redis

# Все логи
docker-compose logs -f
```

## 🔄 Обновление

### Автоматическое обновление

```bash
./docker-scripts.sh update
```

### Ручное обновление

```bash
# Получить последние изменения
git pull

# Пересобрать и перезапустить
./docker-scripts.sh rebuild
```

## 🛠️ Разработка

### Подключение к контейнеру

```bash
./docker-scripts.sh shell
```

### Просмотр файлов

```bash
# Копирование файлов из контейнера
docker cp polza-ai-bot:/app/logs/ ./logs-backup/

# Копирование файлов в контейнер
docker cp ./new-file.py polza-ai-bot:/app/
```

## 🐛 Отладка

### Проблемы с запуском

1. **Проверьте .env файл**:
   ```bash
   cat .env
   ```

2. **Проверьте логи**:
   ```bash
   ./docker-scripts.sh logs
   ```

3. **Проверьте статус**:
   ```bash
   ./docker-scripts.sh status
   ```

### Очистка

```bash
# Очистка неиспользуемых образов
./docker-scripts.sh clean

# Полная очистка (осторожно!)
docker system prune -a
```

## 📈 Производительность

### Оптимизация

- Используйте `docker-compose up -d` для фонового режима
- Настройте логирование для продакшена
- Используйте volume для персистентных данных

### Масштабирование

Для увеличения производительности можно:

1. Увеличить количество реплик бота
2. Настроить Redis кластер
3. Добавить load balancer

## 🔒 Безопасность

- Контейнер запускается под непривилегированным пользователем
- .env файл монтируется как read-only
- Используется минимальный базовый образ (python:3.11-slim)

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `./docker-scripts.sh logs`
2. Проверьте статус: `./docker-scripts.sh status`
3. Перезапустите: `./docker-scripts.sh restart`

---

**Удачного развертывания! 🚀**
