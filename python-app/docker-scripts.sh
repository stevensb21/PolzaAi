#!/bin/bash

# Скрипт для управления Docker контейнерами PolzaAI

case "$1" in
    "build")
        echo "🔨 Сборка Docker образа..."
        docker-compose build
        ;;
    "up")
        echo "🚀 Запуск контейнеров..."
        docker-compose up -d
        ;;
    "down")
        echo "🛑 Остановка контейнеров..."
        docker-compose down
        ;;
    "restart")
        echo "🔄 Перезапуск контейнеров..."
        docker-compose restart
        ;;
    "logs")
        echo "📋 Просмотр логов..."
        docker-compose logs -f polza-ai-bot
        ;;
    "logs-redis")
        echo "📋 Просмотр логов Redis..."
        docker-compose logs -f redis
        ;;
    "status")
        echo "📊 Статус контейнеров..."
        docker-compose ps
        ;;
    "shell")
        echo "🐚 Подключение к контейнеру..."
        docker-compose exec polza-ai-bot /bin/bash
        ;;
    "clean")
        echo "🧹 Очистка неиспользуемых образов и контейнеров..."
        docker system prune -f
        ;;
    "rebuild")
        echo "🔄 Полная пересборка..."
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        ;;
    "update")
        echo "⬆️ Обновление и перезапуск..."
        git pull
        docker-compose down
        docker-compose build
        docker-compose up -d
        ;;
    *)
        echo "🤖 PolzaAI Docker Management Script"
        echo ""
        echo "Использование: $0 {команда}"
        echo ""
        echo "Доступные команды:"
        echo "  build      - Собрать Docker образ"
        echo "  up         - Запустить контейнеры"
        echo "  down       - Остановить контейнеры"
        echo "  restart    - Перезапустить контейнеры"
        echo "  logs       - Показать логи бота"
        echo "  logs-redis - Показать логи Redis"
        echo "  status     - Показать статус контейнеров"
        echo "  shell      - Подключиться к контейнеру"
        echo "  clean      - Очистить неиспользуемые образы"
        echo "  rebuild    - Полная пересборка"
        echo "  update     - Обновить код и перезапустить"
        echo ""
        echo "Примеры:"
        echo "  $0 build && $0 up"
        echo "  $0 logs"
        echo "  $0 shell"
        ;;
esac
