"""
Telegram бот для AI-агента помощника путешественника
"""
import os
import sys
import logging
from dotenv import load_dotenv
import telebot
from telebot import types

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import TravelAgent

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получение токена бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения (.env файл)")

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Инициализация агента (создается один раз при запуске)
try:
    travel_agent = TravelAgent()
    logger.info("Агент инициализирован успешно")
except Exception as e:
    logger.error(f"Ошибка при инициализации агента: {str(e)}")
    travel_agent = None


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Обработка команд /start и /help"""
    welcome_text = """
🌍 *Добро пожаловать в AI-Помощник путешественника!*

Я помогу вам с планированием поездок и путешествий.

*Доступные возможности:*
🌤️ Получение погоды для любого города
🔍 Поиск информации в интернете
✅ Составление чек-листов для поездок
💱 Курсы валют
📱 Генерация QR-кодов для билетов, чек-листов, бронирований
📁 Работа с файлами и расписаниями

*Примеры запросов:*
• Какая погода в Москве?
• Сколько стоит доллар?
• Найди информацию о достопримечательностях Парижа
• Составь чек-лист для поездки в Токио с 1 по 10 января
• Сгенерируй QR-код для билета по ссылке https://www.example.com

Просто напишите ваш вопрос, и я помогу вам!
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')


@bot.message_handler(commands=['status'])
def send_status(message):
    """Проверка статуса бота и агента"""
    if travel_agent:
        status_text = "✅ Бот работает\n✅ Агент активен"
    else:
        status_text = "✅ Бот работает\n❌ Агент не инициализирован"
    bot.reply_to(message, status_text)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработка всех текстовых сообщений"""
    user_id = message.from_user.id
    user_input = message.text
    
    logger.info(f"Получено сообщение от пользователя {user_id}: {user_input}")
    
    # Отправляем сообщение о том, что бот думает
    thinking_msg = bot.reply_to(message, "🤔 Думаю...")
    
    try:
        if not travel_agent:
            bot.edit_message_text(
                "❌ Ошибка: Агент не инициализирован. Проверьте логи.",
                chat_id=message.chat.id,
                message_id=thinking_msg.message_id
            )
            return
        
        # Получаем ответ от агента и список созданных файлов
        response, created_files = travel_agent.run(user_input)
        
        # Если ответ слишком длинный, разбиваем на части
        max_length = 4096  # Максимальная длина сообщения в Telegram
        
        try:
            if len(response) <= max_length:
                bot.edit_message_text(
                    response,
                    chat_id=message.chat.id,
                    message_id=thinking_msg.message_id,
                    parse_mode='Markdown'
                )
            else:
                # Разбиваем длинный ответ на части
                bot.edit_message_text(
                    response[:max_length],
                    chat_id=message.chat.id,
                    message_id=thinking_msg.message_id,
                    parse_mode='Markdown'
                )
                
                # Отправляем остальные части отдельными сообщениями
                remaining = response[max_length:]
                while remaining:
                    chunk = remaining[:max_length]
                    remaining = remaining[max_length:]
                    bot.send_message(
                        message.chat.id,
                        chunk,
                        parse_mode='Markdown'
                    )
        except telebot.apihelper.ApiTelegramException as e:
            # Если не удалось отредактировать сообщение (например, из-за Markdown), отправляем новое
            logger.warning(f"Не удалось отредактировать сообщение, отправляем новое: {str(e)}")
            try:
                bot.delete_message(message.chat.id, thinking_msg.message_id)
            except:
                pass
            
            if len(response) <= max_length:
                bot.send_message(
                    message.chat.id,
                    response
                )
            else:
                # Разбиваем на части без Markdown
                remaining = response
                while remaining:
                    chunk = remaining[:max_length]
                    remaining = remaining[max_length:]
                    bot.send_message(
                        message.chat.id,
                        chunk
                    )
        
        logger.info(f"Ответ отправлен пользователю {user_id}")
        
        # Отправляем созданные файлы пользователю
        if created_files:
            logger.info(f"Отправка {len(created_files)} файлов пользователю {user_id}")
            for filepath in created_files:
                try:
                    # Преобразуем относительный путь в абсолютный, если нужно
                    if not os.path.isabs(filepath):
                        # Если путь относительный, ищем файл в текущей директории или в папке agent
                        agent_dir = os.path.dirname(os.path.abspath(__file__))
                        full_path = os.path.join(agent_dir, filepath)
                        if not os.path.exists(full_path):
                            # Пробуем найти файл в корне проекта
                            project_root = os.path.dirname(agent_dir)
                            full_path = os.path.join(project_root, filepath)
                    else:
                        full_path = filepath
                    
                    # Проверяем, существует ли файл
                    if os.path.exists(full_path):
                        # Определяем тип файла по расширению
                        file_ext = os.path.splitext(full_path)[1].lower()
                        filename = os.path.basename(full_path)
                        
                        with open(full_path, 'rb') as f:
                            # Отправляем файл в зависимости от типа
                            if file_ext in ['.txt', '.md', '.json', '.csv']:
                                # Текстовые файлы отправляем как документ
                                bot.send_document(
                                    message.chat.id,
                                    f,
                                    caption=f"📄 {filename}",
                                    visible_file_name=filename
                                )
                            elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                                # Изображения отправляем как фото
                                bot.send_photo(
                                    message.chat.id,
                                    f,
                                    caption=f"🖼️ {filename}"
                                )
                            elif file_ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']:
                                # Документы отправляем как документ
                                bot.send_document(
                                    message.chat.id,
                                    f,
                                    caption=f"📄 {filename}",
                                    visible_file_name=filename
                                )
                            else:
                                # Остальные файлы отправляем как документ
                                bot.send_document(
                                    message.chat.id,
                                    f,
                                    caption=f"📎 {filename}",
                                    visible_file_name=filename
                                )
                        logger.info(f"Файл {full_path} успешно отправлен")
                    else:
                        logger.warning(f"Файл {full_path} не найден (исходный путь: {filepath})")
                except Exception as e:
                    logger.error(f"Ошибка при отправке файла {filepath}: {str(e)}")
                    try:
                        bot.send_message(
                            message.chat.id,
                            f"❌ Не удалось отправить файл {os.path.basename(filepath)}"
                        )
                    except:
                        pass
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {str(e)}", exc_info=True)
        error_message = f"❌ Произошла ошибка: {str(e)}"
        try:
            bot.edit_message_text(
                error_message,
                chat_id=message.chat.id,
                message_id=thinking_msg.message_id
            )
        except:
            bot.reply_to(message, error_message)


def main():
    """Основная функция запуска бота"""
    logger.info("Запуск Telegram бота...")
    logger.info("Бот готов к работе. Ожидание сообщений...")
    
    try:
        # Запуск бота в режиме polling
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

