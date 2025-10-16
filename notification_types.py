"""
Типы уведомлений для системы охраны труда
"""
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

class NotificationType(Enum):
    """Типы уведомлений"""
    # Сотрудники
    EMPLOYEE_REGISTERED = "employee_registered"
    EMPLOYEE_UPDATED = "employee_updated"
    EMPLOYEE_STATUS_CHANGED = "employee_status_changed"
    
    # Сертификаты
    CERTIFICATE_EXPIRING = "certificate_expiring"
    CERTIFICATE_EXPIRED = "certificate_expired"
    CERTIFICATE_ASSIGNED = "certificate_assigned"
    CERTIFICATE_COMPLETED = "certificate_completed"
    
    # Задачи
    TASK_ASSIGNED = "task_assigned"
    TASK_OVERDUE = "task_overdue"
    TASK_COMPLETED = "task_completed"
    
    # Система
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_ERROR = "system_error"
    DAILY_REPORT = "daily_report"

@dataclass
class NotificationTemplate:
    """Шаблон уведомления"""
    type: NotificationType
    title: str
    message_template: str
    priority: int = 1  # 1-низкий, 2-средний, 3-высокий, 4-критический
    icon: str = "📢"
    requires_action: bool = False

# Шаблоны уведомлений
NOTIFICATION_TEMPLATES = {
    NotificationType.EMPLOYEE_REGISTERED: NotificationTemplate(
        type=NotificationType.EMPLOYEE_REGISTERED,
        title="Новый сотрудник зарегистрирован",
        message_template="""
🎉 <b>Новый сотрудник зарегистрирован!</b>

👤 <b>ФИО:</b> {full_name}
💼 <b>Должность:</b> {position}
📄 <b>СНИЛС:</b> {snils}
🔢 <b>ИНН:</b> {inn}
📞 <b>Телефон:</b> {phone}
📅 <b>Дата рождения:</b> {birth_date}
📊 <b>Статус:</b> {status}
🆔 <b>ID:</b> {employee_id}

🔗 <a href="{search_url}">Посмотреть в системе охраны труда</a>
""",
        priority=2,
        icon="🎉",
        requires_action=True
    ),
    
    NotificationType.EMPLOYEE_UPDATED: NotificationTemplate(
        type=NotificationType.EMPLOYEE_UPDATED,
        title="Данные сотрудника обновлены",
        message_template="""
✅ <b>Сотрудник успешно обновлен!</b>

👤 <b>ФИО:</b> {full_name}
💼 <b>Должность:</b> {position}
📄 <b>СНИЛС:</b> {snils}
🔢 <b>ИНН:</b> {inn}
📞 <b>Телефон:</b> {phone}
📅 <b>Дата рождения:</b> {birth_date}
📊 <b>Статус:</b> {status}
🆔 <b>ID:</b> {employee_id}

🔗 <a href="{search_url}">Посмотреть в системе охраны труда</a>
""",
        priority=2,
        icon="✅"
    ),
    
    NotificationType.CERTIFICATE_EXPIRING: NotificationTemplate(
        type=NotificationType.CERTIFICATE_EXPIRING,
        title="Сертификат скоро истекает",
        message_template="""
⚠️ <b>Внимание! Сертификат скоро истекает</b>

👤 <b>Сотрудник:</b> {employee_name}
📜 <b>Сертификат:</b> {certificate_name}
📅 <b>Истекает:</b> {expiry_date}
⏰ <b>Осталось дней:</b> {days_left}

🔗 <a href="{employee_url}">Посмотреть сотрудника</a>
""",
        priority=3,
        icon="⚠️",
        requires_action=True
    ),
    
    NotificationType.CERTIFICATE_EXPIRED: NotificationTemplate(
        type=NotificationType.CERTIFICATE_EXPIRED,
        title="Сертификат истек!",
        message_template="""
🚨 <b>КРИТИЧНО! Сертификат истек</b>

👤 <b>Сотрудник:</b> {employee_name}
📜 <b>Сертификат:</b> {certificate_name}
📅 <b>Истек:</b> {expiry_date}
⏰ <b>Просрочен на:</b> {days_overdue} дней

🔗 <a href="{employee_url}">Посмотреть сотрудника</a>
""",
        priority=4,
        icon="🚨",
        requires_action=True
    ),
    
    NotificationType.TASK_ASSIGNED: NotificationTemplate(
        type=NotificationType.TASK_ASSIGNED,
        title="Новая задача назначена",
        message_template="""
📋 <b>Вам назначена новая задача</b>

🏢 <b>Процесс:</b> {workflow_name}
👤 <b>Сотрудник:</b> {employee_name}
📝 <b>Описание:</b> {task_description}
📅 <b>Срок:</b> {deadline}

🔗 <a href="{task_url}">Перейти к задаче</a>
""",
        priority=2,
        icon="📋",
        requires_action=True
    ),
    
    NotificationType.DAILY_REPORT: NotificationTemplate(
        type=NotificationType.DAILY_REPORT,
        title="Ежедневный отчет",
        message_template="""
📊 <b>Ежедневный отчет</b>

📈 <b>Статистика за {date}:</b>
• Новых сотрудников: {new_employees}
• Обновлено сотрудников: {updated_employees}
• Истекающих сертификатов: {expiring_certificates}
• Просроченных сертификатов: {expired_certificates}
• Активных задач: {active_tasks}

🔗 <a href="{report_url}">Подробный отчет</a>
""",
        priority=1,
        icon="📊"
    )
}

def get_template(notification_type: NotificationType) -> Optional[NotificationTemplate]:
    """Получить шаблон уведомления по типу"""
    return NOTIFICATION_TEMPLATES.get(notification_type)

def format_notification(template: NotificationTemplate, data: Dict[str, Any]) -> str:
    """Форматировать уведомление по шаблону"""
    try:
        return template.message_template.format(**data)
    except KeyError as e:
        return f"❌ Ошибка форматирования уведомления: отсутствует поле {e}"
    except Exception as e:
        return f"❌ Ошибка форматирования уведомления: {e}"
