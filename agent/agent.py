"""
AI-Агент помощник путешественника
Использует langchain для агентной логики и proxyapi для доступа к LLM
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool, StructuredTool
from langchain_core.messages import HumanMessage, AIMessage

from tools import (
    WeatherTool,
    CurrencyTool,
    WebSearchTool,
    FileIOTool,
    TerminalTool,
    QRCodeTool,
    MemoryTool
)

# Загрузка переменных окружения
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TravelAgent:
    """AI-Агент помощник путешественника"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Инициализация агента
        
        Args:
            api_key: API ключ для proxyapi
            base_url: Базовый URL для proxyapi (если отличается от стандартного)
        """
        self.api_key = api_key or os.getenv("PROXYAPI_API_KEY")
        if not self.api_key:
            raise ValueError("PROXYAPI_API_KEY не установлен в переменных окружения")
        
        # URL для proxyapi (обычно это прокси для OpenAI API)
        self.base_url = base_url or os.getenv("PROXYAPI_BASE_URL", "https://api.openai.com/v1")
        
        logger.info("Инициализация инструментов...")
        
        # Инициализация инструментов
        self.weather_tool = WeatherTool()
        self.currency_tool = CurrencyTool()
        self.web_search_tool = WebSearchTool()
        self.file_io_tool = FileIOTool()
        self.terminal_tool = TerminalTool()
        self.qr_tool = QRCodeTool()
        self.memory_tool = MemoryTool()
        
        # Список созданных файлов для текущего запроса
        self.created_files = []
        
        # Создание инструментов для langchain
        self.tools = self._create_tools()
        
        # Инициализация LLM
        logger.info("Инициализация LLM...")
        self.llm = ChatOpenAI(
            model="gpt-5-2025-08-07",
            temperature=1,  # Модель поддерживает только значение по умолчанию
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60
        )
        
        # Создание агента
        logger.info("Создание агента...")
        self.agent = self._create_agent()
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10
        )
        
        logger.info("Агент инициализирован успешно")
    
    def _write_file_with_tracking(self, filepath: str, content: str) -> str:
        """Обертка для write_file, которая отслеживает созданные файлы"""
        result = self.file_io_tool.write_file(filepath, content)
        if result.get("status") == "success":
            # Добавляем файл в список созданных (используем абсолютный путь из результата)
            file_path = result.get("filepath", filepath)
            self.created_files.append(file_path)
            logger.info(f"Файл добавлен в список для отправки: {file_path}")
        return json.dumps(result, ensure_ascii=False)
    
    def _generate_qr_with_tracking(self, data: str, filename: Optional[str] = None) -> str:
        """Обертка для generate_qr, которая отслеживает созданные QR-коды"""
        result = self.qr_tool.generate_qr(data, filename)
        if result.get("status") == "success" and result.get("filename"):
            # Добавляем QR-код в список созданных файлов
            qr_path = result.get("filename")
            self.created_files.append(qr_path)
            logger.info(f"QR-код добавлен в список для отправки: {qr_path}")
        return json.dumps(result, ensure_ascii=False)
    
    def _create_tools(self) -> list:
        """Создает список инструментов для агента"""
        tools = [
            Tool(
                name="get_weather",
                func=lambda city: json.dumps(self.weather_tool.get_weather(city), ensure_ascii=False),
                description=(
                    "Получает текущую погоду для указанного города. "
                    "Принимает название города (например: 'Москва', 'Paris', 'New York'). "
                    "Возвращает температуру, скорость ветра и условия погоды."
                )
            ),
            Tool(
                name="get_currency_rate",
                func=lambda currency: json.dumps(self.currency_tool.get_exchange_rate(currency), ensure_ascii=False),
                description=(
                    "Получает курс валюты относительно рубля. "
                    "Принимает код валюты (например: 'USD', 'EUR', 'GBP'). "
                    "Возвращает курс обмена."
                )
            ),
            Tool(
                name="web_search",
                func=lambda query: json.dumps(self.web_search_tool.search(query), ensure_ascii=False),
                description=(
                    "Выполняет поиск информации в интернете. "
                    "Используй для поиска информации о достопримечательностях, отелях, "
                    "расписании транспорта, климате, отзывах и другой информации для путешествий. "
                    "Принимает поисковый запрос на естественном языке."
                )
            ),
            Tool(
                name="read_file",
                func=lambda filepath: json.dumps(self.file_io_tool.read_file(filepath), ensure_ascii=False),
                description=(
                    "Читает содержимое файла. "
                    "Принимает путь к файлу. "
                    "Используй для чтения сохраненных данных, чек-листов, расписаний."
                )
            ),
            StructuredTool.from_function(
                func=lambda filepath, content: self._write_file_with_tracking(filepath, content),
                name="write_file",
                description=(
                    "Записывает данные в файл. "
                    "Принимает filepath (путь к файлу) и content (содержимое). "
                    "Используй для сохранения чек-листов, расписаний, заметок."
                )
            ),
            Tool(
                name="execute_terminal",
                func=lambda command: json.dumps(self.terminal_tool.execute(command), ensure_ascii=False),
                description=(
                    "Выполняет безопасную терминальную команду. "
                    "Разрешены только базовые команды: ls, dir, pwd, echo, cat, type, date, time. "
                    "Используй осторожно и только для простых операций."
                )
            ),
            StructuredTool.from_function(
                func=lambda data, filename=None: self._generate_qr_with_tracking(data, filename),
                name="generate_qr_code",
                description=(
                    "Генерирует QR-код для данных. "
                    "Принимает data (данные для кодирования) и filename (опционально, путь для сохранения). "
                    "Используй для создания QR-кодов билетов, бронирований, контактов. "
                    "ВАЖНО: Всегда указывай filename при создании QR-кода, чтобы файл можно было отправить пользователю."
                )
            ),
        ]
        
        return tools
    
    def _create_agent(self):
        """Создает агента с промптом"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Ты - AI-помощник путешественника. Твоя задача - помогать пользователям планировать поездки, 
получать информацию о погоде, курсах валют, достопримечательностях и других важных вещах для путешествий.

Твои возможности:
1. Получение актуальной погоды для любого города
2. Поиск информации в интернете (достопримечательности, отели, транспорт, климат, отзывы)
3. Помощь в составлении чек-листов для поездок
4. Получение курсов валют
5. Генерация QR-кодов для билетов и бронирований
6. Работа с файлами (сохранение расписаний, чек-листов)
7. Безопасное выполнение терминальных команд

Правила работы:
- Всегда анализируй запрос пользователя и выбирай подходящий инструмент
- Если информации недостаточно, задавай уточняющие вопросы
- Предоставляй структурированные и понятные ответы
- Для составления чек-листов учитывай: локацию, даты поездки, погоду, климат
- Сохраняй важную информацию в файлы для последующего использования
- Будь вежливым и полезным

Используй доступные инструменты для выполнения задач пользователя."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        return agent
    
    def run(self, user_input: str, chat_history: Optional[list] = None) -> tuple:
        """
        Запускает агента с пользовательским запросом
        
        Args:
            user_input: Запрос пользователя
            chat_history: История диалога (опционально)
            
        Returns:
            Кортеж (ответ агента, список созданных файлов)
        """
        try:
            # Очищаем список созданных файлов перед новым запросом
            self.created_files = []
            
            logger.info(f"Получен запрос пользователя: {user_input}")
            
            # Получаем контекст из памяти
            context = self.memory_tool.get_context()
            
            # Подготовка истории диалога
            if chat_history is None:
                chat_history = []
            
            # Добавляем контекст к запросу, если есть
            if context:
                enhanced_input = f"Контекст предыдущих разговоров:\n{context}\n\nТекущий запрос: {user_input}"
            else:
                enhanced_input = user_input
            
            # Выполнение агента
            logger.info("Запуск агента...")
            result = self.agent_executor.invoke({
                "input": enhanced_input,
                "chat_history": chat_history
            })
            
            response = result.get("output", "Извините, не удалось обработать запрос.")
            
            logger.info(f"Ответ агента: {response[:200]}...")
            
            # Сохранение в память
            self.memory_tool.add_conversation(user_input, response)
            
            # Возвращаем ответ и список созданных файлов
            created_files = self.created_files.copy()
            if created_files:
                logger.info(f"Создано файлов для отправки: {len(created_files)}")
            
            return response, created_files
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении агента: {str(e)}", exc_info=True)
            error_msg = f"Произошла ошибка: {str(e)}"
            self.memory_tool.add_conversation(user_input, error_msg)
            return error_msg, []
    
    def create_travel_checklist(self, location: str, dates: str, weather_info: Optional[Dict] = None) -> tuple:
        """
        Создает чек-лист для поездки на основе локации, дат и погоды
        
        Args:
            location: Место назначения
            dates: Даты поездки
            weather_info: Информация о погоде (опционально)
            
        Returns:
            Кортеж (текст чек-листа, список созданных файлов)
        """
        checklist_prompt = f"""Составь подробный чек-лист для поездки:
Локация: {location}
Даты: {dates}
Погода: {weather_info if weather_info else 'не указана'}

Включи:
- Документы (паспорт, виза, билеты, страховка)
- Одежда (с учетом погоды и климата)
- Электроника и зарядные устройства
- Личные вещи
- Медикаменты
- Деньги и банковские карты
- Другие важные вещи для этой локации"""
        
        return self.run(checklist_prompt)


def run_agent(user_input: str) -> str:
    """
    Функция для запуска агента (используется в run.py)
    
    Args:
        user_input: Запрос пользователя
        
    Returns:
        Ответ агента
    """
    try:
        agent = TravelAgent()
        response, _ = agent.run(user_input)
        return response
    except Exception as e:
        logger.error(f"Ошибка при инициализации агента: {str(e)}")
        return f"Ошибка: {str(e)}"

