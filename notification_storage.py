"""
Система хранения настроек уведомлений
"""
import json
import os
from typing import Dict, List, Set, Optional
from datetime import datetime
from notification_types import NotificationType

class NotificationStorage:
    """Хранилище настроек уведомлений"""
    
    def __init__(self, storage_file: str = "notification_settings.json"):
        self.storage_file = storage_file
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict:
        """Загрузить настройки из файла"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Настройки по умолчанию
        return {
            "user_subscriptions": {},  # user_id -> [notification_types]
            "user_preferences": {},    # user_id -> {settings}
            "system_settings": {
                "enabled": True,
                "check_interval": 3600,  # секунды
                "max_notifications_per_hour": 10,
                "retry_attempts": 3
            },
            "last_check": None,
            "notification_history": []
        }
    
    def _save_settings(self):
        """Сохранить настройки в файл"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
    def subscribe_user(self, user_id: str, notification_types: List[NotificationType]):
        """Подписать пользователя на типы уведомлений"""
        if user_id not in self.settings["user_subscriptions"]:
            self.settings["user_subscriptions"][user_id] = []
        
        # Добавляем новые типы уведомлений
        current_types = set(self.settings["user_subscriptions"][user_id])
        new_types = set([nt.value for nt in notification_types])
        self.settings["user_subscriptions"][user_id] = list(current_types.union(new_types))
        
        self._save_settings()
    
    def unsubscribe_user(self, user_id: str, notification_types: Optional[List[NotificationType]] = None):
        """Отписать пользователя от уведомлений"""
        if notification_types is None:
            # Отписать от всех уведомлений
            if user_id in self.settings["user_subscriptions"]:
                del self.settings["user_subscriptions"][user_id]
        else:
            # Отписать от конкретных типов
            if user_id in self.settings["user_subscriptions"]:
                current_types = set(self.settings["user_subscriptions"][user_id])
                remove_types = set([nt.value for nt in notification_types])
                self.settings["user_subscriptions"][user_id] = list(current_types - remove_types)
        
        self._save_settings()
    
    def get_user_subscriptions(self, user_id: str) -> List[str]:
        """Получить подписки пользователя"""
        return self.settings["user_subscriptions"].get(user_id, [])
    
    def is_user_subscribed(self, user_id: str, notification_type: NotificationType) -> bool:
        """Проверить, подписан ли пользователь на тип уведомления"""
        user_subscriptions = self.get_user_subscriptions(user_id)
        return notification_type.value in user_subscriptions
    
    def get_subscribers(self, notification_type: NotificationType) -> List[str]:
        """Получить список подписчиков на тип уведомления"""
        subscribers = []
        for user_id, subscriptions in self.settings["user_subscriptions"].items():
            if notification_type.value in subscriptions:
                subscribers.append(user_id)
        return subscribers
    
    def set_user_preference(self, user_id: str, key: str, value: any):
        """Установить предпочтение пользователя"""
        if user_id not in self.settings["user_preferences"]:
            self.settings["user_preferences"][user_id] = {}
        
        self.settings["user_preferences"][user_id][key] = value
        self._save_settings()
    
    def get_user_preference(self, user_id: str, key: str, default=None):
        """Получить предпочтение пользователя"""
        return self.settings["user_preferences"].get(user_id, {}).get(key, default)
    
    def add_notification_history(self, user_id: str, notification_type: NotificationType, 
                               success: bool, error_message: str = None):
        """Добавить запись в историю уведомлений"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "notification_type": notification_type.value,
            "success": success,
            "error_message": error_message
        }
        
        self.settings["notification_history"].append(history_entry)
        
        # Ограничиваем размер истории (последние 1000 записей)
        if len(self.settings["notification_history"]) > 1000:
            self.settings["notification_history"] = self.settings["notification_history"][-1000:]
        
        self._save_settings()
    
    def get_notification_stats(self, hours: int = 24) -> Dict:
        """Получить статистику уведомлений за период"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        recent_history = [
            entry for entry in self.settings["notification_history"]
            if datetime.fromisoformat(entry["timestamp"]).timestamp() > cutoff_time
        ]
        
        total_sent = len(recent_history)
        successful = len([e for e in recent_history if e["success"]])
        failed = total_sent - successful
        
        return {
            "total_sent": total_sent,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total_sent * 100) if total_sent > 0 else 0
        }
    
    def get_system_settings(self) -> Dict:
        """Получить системные настройки"""
        return self.settings["system_settings"]
    
    def update_system_settings(self, settings: Dict):
        """Обновить системные настройки"""
        self.settings["system_settings"].update(settings)
        self._save_settings()
    
    def is_system_enabled(self) -> bool:
        """Проверить, включена ли система уведомлений"""
        return self.settings["system_settings"].get("enabled", True)
    
    def set_system_enabled(self, enabled: bool):
        """Включить/выключить систему уведомлений"""
        self.settings["system_settings"]["enabled"] = enabled
        self._save_settings()
