"""
Планировщик уведомлений
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from notification_types import NotificationType, get_template, format_notification
from notification_storage import NotificationStorage
from api import allPeople, getPeople

logger = logging.getLogger(__name__)

class NotificationScheduler:
    """Планировщик уведомлений"""
    
    def __init__(self, bot, storage: NotificationStorage):
        self.bot = bot
        self.storage = storage
        self.running = False
        self.task = None
    
    async def start(self):
        """Запустить планировщик"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info("Планировщик уведомлений запущен")
    
    async def stop(self):
        """Остановить планировщик"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Планировщик уведомлений остановлен")
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                if self.storage.is_system_enabled():
                    await self._check_and_send_notifications()
                
                # Ждем интервал проверки
                check_interval = self.storage.get_system_settings().get("check_interval", 3600)
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Ошибка в планировщике уведомлений: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    async def _check_and_send_notifications(self):
        """Проверить и отправить уведомления"""
        logger.info("Проверка уведомлений...")
        
        # Проверяем истекающие сертификаты
        await self._check_expiring_certificates()
        
        # Проверяем просроченные сертификаты
        await self._check_expired_certificates()
        
        # Проверяем просроченные задачи
        await self._check_overdue_tasks()
        
        logger.info("Проверка уведомлений завершена")
    
    async def _check_expiring_certificates(self):
        """Проверить истекающие сертификаты"""
        try:
            # Получаем всех сотрудников
            all_people = await allPeople()
            if not all_people or isinstance(all_people, dict) and all_people.get("error"):
                return
            
            # allPeople() возвращает список напрямую
            employees = all_people if isinstance(all_people, list) else []
            expiring_days = [7, 30]  # Проверяем за 7 и 30 дней
            
            for employee in employees:
                employee_id = employee.get("id")
                full_name = employee.get("full_name")
                all_certificates = employee.get("all_certificates", [])
                
                for certificate in all_certificates:
                    if certificate.get("is_assigned", False):
                        expiry_date_str = certificate.get("assigned_data", {}).get("expiry_date")
                        if expiry_date_str:
                            try:
                                expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
                                days_until_expiry = (expiry_date - datetime.now()).days
                                
                                if days_until_expiry in expiring_days:
                                    await self._send_certificate_expiring_notification(
                                        employee_id, full_name, certificate, days_until_expiry
                                    )
                            except Exception as e:
                                logger.error(f"Ошибка обработки даты сертификата: {e}")
                                
        except Exception as e:
            logger.error(f"Ошибка проверки истекающих сертификатов: {e}")
    
    async def _check_expired_certificates(self):
        """Проверить просроченные сертификаты"""
        try:
            all_people = await allPeople()
            if not all_people or isinstance(all_people, dict) and all_people.get("error"):
                return
            
            # allPeople() возвращает список напрямую
            employees = all_people if isinstance(all_people, list) else []
            
            for employee in employees:
                employee_id = employee.get("id")
                full_name = employee.get("full_name")
                all_certificates = employee.get("all_certificates", [])
                
                for certificate in all_certificates:
                    if certificate.get("is_assigned", False):
                        expiry_date_str = certificate.get("assigned_data", {}).get("expiry_date")
                        if expiry_date_str:
                            try:
                                expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
                                
                                if expiry_date < datetime.now():
                                    days_overdue = (datetime.now() - expiry_date).days
                                    await self._send_certificate_expired_notification(
                                        employee_id, full_name, certificate, days_overdue
                                    )
                            except Exception as e:
                                logger.error(f"Ошибка обработки даты сертификата: {e}")
                                
        except Exception as e:
            logger.error(f"Ошибка проверки просроченных сертификатов: {e}")
    
    async def _check_overdue_tasks(self):
        """Проверить просроченные задачи (заглушка)"""
        # Здесь можно добавить логику проверки просроченных задач
        pass
    
    async def _send_certificate_expiring_notification(self, employee_id: int, employee_name: str, 
                                                    certificate: Dict, days_left: int):
        """Отправить уведомление об истекающем сертификате"""
        template = get_template(NotificationType.CERTIFICATE_EXPIRING)
        if not template:
            return
        
        # Получаем подписчиков
        subscribers = self.storage.get_subscribers(NotificationType.CERTIFICATE_EXPIRING)
        
        data = {
            "employee_name": employee_name,
            "certificate_name": certificate.get("name", "Неизвестно"),
            "expiry_date": certificate.get("assigned_data", {}).get("expiry_date", "Неизвестно"),
            "days_left": days_left,
            "employee_url": f"http://labor.tetrakom-crm-miniapp.ru/safety?search_fio={employee_name}"
        }
        
        message = format_notification(template, data)
        
        for user_id in subscribers:
            try:
                await self.bot.send_message(int(user_id), message, parse_mode='HTML')
                self.storage.add_notification_history(user_id, NotificationType.CERTIFICATE_EXPIRING, True)
                logger.info(f"Уведомление об истекающем сертификате отправлено пользователю {user_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
                self.storage.add_notification_history(user_id, NotificationType.CERTIFICATE_EXPIRING, False, str(e))
    
    async def _send_certificate_expired_notification(self, employee_id: int, employee_name: str, 
                                                    certificate: Dict, days_overdue: int):
        """Отправить уведомление о просроченном сертификате"""
        template = get_template(NotificationType.CERTIFICATE_EXPIRED)
        if not template:
            return
        
        subscribers = self.storage.get_subscribers(NotificationType.CERTIFICATE_EXPIRED)
        
        data = {
            "employee_name": employee_name,
            "certificate_name": certificate.get("name", "Неизвестно"),
            "expiry_date": certificate.get("assigned_data", {}).get("expiry_date", "Неизвестно"),
            "days_overdue": days_overdue,
            "employee_url": f"http://labor.tetrakom-crm-miniapp.ru/safety?search_fio={employee_name}"
        }
        
        message = format_notification(template, data)
        
        for user_id in subscribers:
            try:
                await self.bot.send_message(int(user_id), message, parse_mode='HTML')
                self.storage.add_notification_history(user_id, NotificationType.CERTIFICATE_EXPIRED, True)
                logger.info(f"Уведомление о просроченном сертификате отправлено пользователю {user_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
                self.storage.add_notification_history(user_id, NotificationType.CERTIFICATE_EXPIRED, False, str(e))
    
    async def send_immediate_notification(self, notification_type: NotificationType, 
                                        data: Dict[str, Any], user_ids: List[str] = None):
        """Отправить немедленное уведомление"""
        template = get_template(notification_type)
        if not template:
            logger.error(f"Шаблон для типа уведомления {notification_type} не найден")
            return
        
        message = format_notification(template, data)
        
        if user_ids is None:
            user_ids = self.storage.get_subscribers(notification_type)
        
        for user_id in user_ids:
            try:
                await self.bot.send_message(int(user_id), message, parse_mode='HTML')
                self.storage.add_notification_history(user_id, notification_type, True)
                logger.info(f"Немедленное уведомление {notification_type.value} отправлено пользователю {user_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки немедленного уведомления пользователю {user_id}: {e}")
                self.storage.add_notification_history(user_id, notification_type, False, str(e))
    
    async def send_immediate_notification_with_photo(self, notification_type: NotificationType, 
                                                   data: Dict[str, Any], user_ids: List[str], 
                                                   source_user_id: int, photo_file_id: str = None):
        """Отправить немедленное уведомление с фото"""
        template = get_template(notification_type)
        if not template:
            logger.error(f"Шаблон для типа уведомления {notification_type} не найден")
            return
        
        message = format_notification(template, data)
        
        logger.info(f"Получено фото для source_user_id {source_user_id}: {photo_file_id}")
        
        for user_id in user_ids:
            try:
                if photo_file_id:
                    # Отправляем сообщение с фото
                    await self.bot.send_photo(
                        int(user_id), 
                        photo_file_id, 
                        caption=message, 
                        parse_mode='HTML'
                    )
                    logger.info(f"Уведомление с фото {notification_type.value} отправлено пользователю {user_id}")
                else:
                    # Отправляем обычное сообщение без фото
                    await self.bot.send_message(int(user_id), message, parse_mode='HTML')
                    logger.info(f"Уведомление без фото {notification_type.value} отправлено пользователю {user_id}")
                
                self.storage.add_notification_history(user_id, notification_type, True)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления с фото пользователю {user_id}: {e}")
                self.storage.add_notification_history(user_id, notification_type, False, str(e))
        
        # Очищаем фото после отправки всех уведомлений
        if photo_file_id:
            from telegram_bot import user_photos
            if source_user_id in user_photos:
                del user_photos[source_user_id]
                logger.info(f"Фото очищено для пользователя {source_user_id}")
    
    async def send_immediate_notification_with_photo_and_docx(self, notification_type: NotificationType, 
                                                           data: Dict[str, Any], user_ids: List[str], 
                                                           source_user_id: int, photo_file_id: str = None, 
                                                           docx_filename: str = None):
        """Отправить немедленное уведомление с фото и DOCX файлом"""
        template = get_template(notification_type)
        if not template:
            logger.error(f"Шаблон для типа уведомления {notification_type} не найден")
            return
        
        message = format_notification(template, data)
        
        logger.info(f"Получено фото для source_user_id {source_user_id}: {photo_file_id}")
        logger.info(f"Получен DOCX файл: {docx_filename}")
        
        for user_id in user_ids:
            try:
                if photo_file_id and docx_filename:
                    # Отправляем сначала фото с текстом
                    await self.bot.send_photo(
                        int(user_id), 
                        photo_file_id, 
                        caption=message, 
                        parse_mode='HTML'
                    )
                    logger.info(f"Уведомление с фото {notification_type.value} отправлено пользователю {user_id}")
                    
                    # Затем отправляем DOCX файл отдельно
                    with open(docx_filename, 'rb') as docx_file:
                        await self.bot.send_document(
                            int(user_id), 
                            docx_file,
                            caption="📄 Документ с данными сотрудника",
                            parse_mode='HTML'
                        )
                    logger.info(f"DOCX файл {notification_type.value} отправлен пользователю {user_id}")
                elif photo_file_id:
                    # Отправляем сообщение только с фото
                    await self.bot.send_photo(
                        int(user_id), 
                        photo_file_id, 
                        caption=message, 
                        parse_mode='HTML'
                    )
                    logger.info(f"Уведомление с фото {notification_type.value} отправлено пользователю {user_id}")
                elif docx_filename:
                    # Отправляем сообщение только с DOCX файлом
                    with open(docx_filename, 'rb') as docx_file:
                        await self.bot.send_document(
                            int(user_id), 
                            docx_file,
                            caption=message, 
                            parse_mode='HTML'
                        )
                    logger.info(f"Уведомление с DOCX файлом {notification_type.value} отправлено пользователю {user_id}")
                else:
                    # Отправляем обычное сообщение без фото и файлов
                    await self.bot.send_message(int(user_id), message, parse_mode='HTML')
                    logger.info(f"Уведомление без фото и файлов {notification_type.value} отправлено пользователю {user_id}")
                
                self.storage.add_notification_history(user_id, notification_type, True)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления с фото и DOCX пользователю {user_id}: {e}")
                self.storage.add_notification_history(user_id, notification_type, False, str(e))
        
        # Очищаем фото после отправки всех уведомлений
        if photo_file_id:
            from telegram_bot import user_photos
            if source_user_id in user_photos:
                del user_photos[source_user_id]
                logger.info(f"Фото очищено для пользователя {source_user_id}")
        
        # Очищаем DOCX файл после отправки
        if docx_filename:
            try:
                import os
                os.remove(docx_filename)
                logger.info(f"DOCX файл удален: {docx_filename}")
            except Exception as e:
                logger.error(f"Ошибка удаления DOCX файла {docx_filename}: {e}")
