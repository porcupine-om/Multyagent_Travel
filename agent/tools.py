"""
Инструменты для AI-агента помощника путешественника
"""
import json
import os
import logging
import subprocess
from typing import Optional, Dict, Any
import requests
from geopy.geocoders import Nominatim
import qrcode
from io import BytesIO
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherTool:
    """Инструмент для получения погоды через open-meteo.com"""
    
    @staticmethod
    def get_weather(city: str) -> Dict[str, Any]:
        """
        Получает текущую погоду для указанного города
        
        Args:
            city: Название города
            
        Returns:
            Словарь с данными о погоде
        """
        try:
            logger.info(f"Получение погоды для города: {city}")
            
            # Геокодирование: получение координат города
            geolocator = Nominatim(user_agent="travel_agent")
            location = geolocator.geocode(city)
            
            if not location:
                return {"error": f"Город '{city}' не найден"}
            
            lat = location.latitude
            lon = location.longitude
            
            logger.info(f"Координаты города {city}: {lat}, {lon}")
            
            # Запрос погоды
            url = f"https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "timezone": "auto"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "current_weather" in data:
                weather = data["current_weather"]
                result = {
                    "city": city,
                    "temperature": weather.get("temperature", "N/A"),
                    "windspeed": weather.get("windspeed", "N/A"),
                    "winddirection": weather.get("winddirection", "N/A"),
                    "weathercode": weather.get("weathercode", "N/A"),
                    "time": weather.get("time", "N/A")
                }
                logger.info(f"Погода получена: {result}")
                return result
            else:
                return {"error": "Данные о погоде не найдены"}
                
        except Exception as e:
            logger.error(f"Ошибка при получении погоды: {str(e)}")
            return {"error": f"Ошибка при получении погоды: {str(e)}"}


class CurrencyTool:
    """Инструмент для получения курсов валют через exchangerate-api.com"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EXCHANGERATE_API_KEY", "")
        if not self.api_key:
            logger.warning("EXCHANGERATE_API_KEY не установлен, используем бесплатный режим")
    
    def get_exchange_rate(self, currency: str) -> Dict[str, Any]:
        """
        Получает курс валюты относительно рубля
        
        Args:
            currency: Код валюты (USD, EUR, и т.д.)
            
        Returns:
            Словарь с курсом валюты
        """
        try:
            currency = currency.upper()
            logger.info(f"Получение курса валюты: {currency}")
            
            if self.api_key:
                # Используем API с ключом
                url = f"https://v6.exchangerate-api.com/v6/{self.api_key}/latest/RUB"
            else:
                # Бесплатный вариант через альтернативный API
                url = f"https://api.exchangerate-api.com/v4/latest/RUB"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "rates" in data:
                rates = data["rates"]
                if currency in rates:
                    rate = rates[currency]
                    result = {
                        "currency": currency,
                        "rate_to_rub": rate,
                        "rub_to_currency": 1 / rate if rate > 0 else 0,
                        "base": "RUB"
                    }
                    logger.info(f"Курс получен: {result}")
                    return result
                else:
                    return {"error": f"Валюта '{currency}' не найдена"}
            else:
                return {"error": "Данные о курсах не найдены"}
                
        except Exception as e:
            logger.error(f"Ошибка при получении курса валют: {str(e)}")
            return {"error": f"Ошибка при получении курса валют: {str(e)}"}


class WebSearchTool:
    """Инструмент для поиска в интернете через DuckDuckGo"""
    
    @staticmethod
    def search(query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Выполняет поиск в интернете
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            
        Returns:
            Словарь с результатами поиска
        """
        try:
            logger.info(f"Поиск в интернете: {query}")
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            if results:
                formatted_results = []
                for r in results:
                    formatted_results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    })
                
                logger.info(f"Найдено результатов: {len(formatted_results)}")
                return {
                    "query": query,
                    "results": formatted_results,
                    "count": len(formatted_results)
                }
            else:
                return {"query": query, "results": [], "count": 0}
                
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")
            return {"error": f"Ошибка при поиске: {str(e)}"}


class FileIOTool:
    """Инструмент для работы с файловой системой"""
    
    @staticmethod
    def read_file(filepath: str) -> Dict[str, Any]:
        """
        Читает файл
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            Содержимое файла
        """
        try:
            logger.info(f"Чтение файла: {filepath}")
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"filepath": filepath, "content": content}
        except Exception as e:
            logger.error(f"Ошибка при чтении файла: {str(e)}")
            return {"error": f"Ошибка при чтении файла: {str(e)}"}
    
    @staticmethod
    def write_file(filepath: str, content: str) -> Dict[str, Any]:
        """
        Записывает файл
        
        Args:
            filepath: Путь к файлу (может быть относительным или абсолютным)
            content: Содержимое для записи
            
        Returns:
            Результат операции с абсолютным путем к файлу
        """
        try:
            logger.info(f"Запись файла: {filepath}")
            
            # Если путь относительный, сохраняем в папке agent
            if not os.path.isabs(filepath):
                # Получаем директорию, где находится tools.py
                tools_dir = os.path.dirname(os.path.abspath(__file__))
                filepath = os.path.join(tools_dir, filepath)
            
            # Создаем директории, если их нет
            dir_path = os.path.dirname(filepath)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            # Записываем файл
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Возвращаем абсолютный путь
            abs_path = os.path.abspath(filepath)
            logger.info(f"Файл успешно сохранен: {abs_path}")
            return {"filepath": abs_path, "status": "success"}
        except Exception as e:
            logger.error(f"Ошибка при записи файла: {str(e)}")
            return {"error": f"Ошибка при записи файла: {str(e)}"}


class TerminalTool:
    """Инструмент для выполнения безопасных терминальных команд"""
    
    # Разрешенные команды для безопасности
    ALLOWED_COMMANDS = ['ls', 'dir', 'pwd', 'cd', 'echo', 'cat', 'type', 'date', 'time']
    
    @staticmethod
    def execute(command: str) -> Dict[str, Any]:
        """
        Выполняет безопасную терминальную команду
        
        Args:
            command: Команда для выполнения
            
        Returns:
            Результат выполнения команды
        """
        try:
            logger.info(f"Выполнение команды: {command}")
            
            # Проверка безопасности
            cmd_parts = command.strip().split()
            if not cmd_parts:
                return {"error": "Пустая команда"}
            
            base_cmd = cmd_parts[0].lower()
            if base_cmd not in TerminalTool.ALLOWED_COMMANDS:
                return {"error": f"Команда '{base_cmd}' не разрешена для безопасности"}
            
            # Выполнение команды
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Команда превысила время выполнения")
            return {"error": "Команда превысила время выполнения"}
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды: {str(e)}")
            return {"error": f"Ошибка при выполнении команды: {str(e)}"}


class QRCodeTool:
    """Инструмент для генерации QR-кодов"""
    
    @staticmethod
    def generate_qr(data: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Генерирует QR-код для данных
        
        Args:
            data: Данные для кодирования
            filename: Имя файла для сохранения (опционально, может быть относительным или абсолютным)
            
        Returns:
            Информация о созданном QR-коде с абсолютным путем к файлу
        """
        try:
            logger.info(f"Генерация QR-кода для данных: {data[:50]}...")
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            if filename:
                # Если путь относительный, сохраняем в папке agent
                if not os.path.isabs(filename):
                    # Получаем директорию, где находится tools.py
                    tools_dir = os.path.dirname(os.path.abspath(__file__))
                    filename = os.path.join(tools_dir, filename)
                
                # Создаем директории, если их нет
                dir_path = os.path.dirname(filename)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                
                # Сохраняем QR-код
                img.save(filename)
                
                # Возвращаем абсолютный путь
                abs_path = os.path.abspath(filename)
                logger.info(f"QR-код сохранен в файл: {abs_path}")
                return {"status": "success", "filename": abs_path, "data_length": len(data)}
            else:
                # Возвращаем base64 для отображения
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                img_str = base64.b64encode(buffer.getvalue()).decode()
                return {
                    "status": "success",
                    "data_length": len(data),
                    "image_base64": img_str[:100] + "..."  # Первые 100 символов для предпросмотра
                }
                
        except Exception as e:
            logger.error(f"Ошибка при генерации QR-кода: {str(e)}")
            return {"error": f"Ошибка при генерации QR-кода: {str(e)}"}


class MemoryTool:
    """Инструмент для работы с долговременной памятью агента"""
    
    def __init__(self, memory_file: str = "memory.json"):
        self.memory_file = memory_file
        self.memory = self._load_memory()
    
    def _load_memory(self) -> Dict[str, Any]:
        """Загружает память из файла"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"conversations": [], "context": {}}
        except Exception as e:
            logger.error(f"Ошибка при загрузке памяти: {str(e)}")
            return {"conversations": [], "context": {}}
    
    def save_memory(self):
        """Сохраняет память в файл"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
            logger.info(f"Память сохранена в {self.memory_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении памяти: {str(e)}")
    
    def add_conversation(self, user_query: str, agent_response: str, summary: Optional[str] = None):
        """Добавляет разговор в память"""
        conversation = {
            "user_query": user_query,
            "agent_response": agent_response,
            "summary": summary or agent_response[:200],
            "timestamp": str(os.path.getmtime(self.memory_file) if os.path.exists(self.memory_file) else "")
        }
        self.memory["conversations"].append(conversation)
        # Ограничиваем размер истории (последние 100 разговоров)
        if len(self.memory["conversations"]) > 100:
            self.memory["conversations"] = self.memory["conversations"][-100:]
        self.save_memory()
    
    def get_context(self) -> str:
        """Возвращает контекст для агента"""
        if not self.memory["conversations"]:
            return ""
        
        # Берем последние 5 разговоров для контекста
        recent = self.memory["conversations"][-5:]
        context_parts = []
        for conv in recent:
            context_parts.append(f"Пользователь: {conv['user_query']}")
            context_parts.append(f"Агент: {conv['summary']}")
        
        return "\n".join(context_parts)

