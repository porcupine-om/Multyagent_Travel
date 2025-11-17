"""
CLI интерфейс для запуска AI-агента помощника путешественника
"""
import sys
import os
import logging

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import run_agent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция CLI интерфейса"""
    print("=" * 60)
    print("AI-Агент Помощник Путешественника")
    print("=" * 60)
    print("\nДоступные возможности:")
    print("- Получение погоды для любого города")
    print("- Поиск информации в интернете")
    print("- Составление чек-листов для поездок")
    print("- Курсы валют")
    print("- Генерация QR-кодов")
    print("- Работа с файлами и расписаниями")
    print("\nВведите 'exit' или 'quit' для выхода")
    print("Введите 'help' для справки")
    print("=" * 60)
    print()
    
    # Интерактивный режим
    while True:
        try:
            user_input = input("\nВы: ").strip()
            
            if not user_input:
                continue
            
            # Команды выхода
            if user_input.lower() in ['exit', 'quit', 'выход']:
                print("\nДо свидания! Хороших путешествий!")
                break
            
            # Справка
            if user_input.lower() in ['help', 'помощь']:
                print("\nПримеры запросов:")
                print("- Какая погода в Москве?")
                print("- Сколько стоит доллар?")
                print("- Найди информацию о достопримечательностях Парижа")
                print("- Составь чек-лист для поездки в Токио с 1 по 10 января")
                print("- Сгенерируй QR-код для билета: ABC123")
                continue
            
            # Обработка запроса
            print("\nАгент думает...")
            response = run_agent(user_input)
            print(f"\nАгент: {response}")
            
        except KeyboardInterrupt:
            print("\n\nПрервано пользователем. До свидания!")
            break
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}", exc_info=True)
            print(f"\nПроизошла ошибка: {str(e)}")


if __name__ == "__main__":
    main()

