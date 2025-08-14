from dataclasses import dataclass, field
from typing import List, Dict, Any
import uuid
from datetime import datetime

from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from loguru import logger

from models.risk import Risk
from utils.json_extractor import Extractor
from utils.text_processor import TextProcessor


@dataclass
class RiskExtractor:
    """Класс для извлечения рисков из документов"""
    
    llm: BaseChatModel
    extractor: Extractor
    text_processor: TextProcessor
    
    _risk_extraction_chain: Runnable[dict, str] = field(init=False)
    
    def __post_init__(self):
        # Загружаем промпт для извлечения рисков
        prompt_content = self._load_prompt("risk_extraction")
        risk_extraction_template = ChatPromptTemplate.from_messages([
            ("system", prompt_content)
        ])
        
        self._risk_extraction_chain = risk_extraction_template | self.llm | StrOutputParser()
    
    def _load_prompt(self, prompt_name: str) -> str:
        """Загружает промпт из файла"""
        try:
            import os

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prompt_path = os.path.join(project_root, 'promts', f"{prompt_name}.md")
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                # Проверяем, что промпт содержит нужные переменные
                if "{documents_content}" not in content or "{question_topic}" not in content:
                    logger.warning(f"Промпт {prompt_name} не содержит ожидаемых переменных")
                return content
        except FileNotFoundError:
            logger.warning(f"Промпт {prompt_name} не найден, используем базовый")
            return self._get_base_prompt()
        except Exception as e:
            logger.error(f"Ошибка при загрузке промпта {prompt_name}: {e}")
            return self._get_base_prompt()

    
    def _get_base_prompt(self) -> str:
        """Возвращает базовый промпт если файл не найден"""
        return """
        Ты - эксперт по анализу рисков. Проанализируй документы и выяви все возможные риски.
        Верни результат в формате JSON с полем "risks", содержащим массив рисков.
        """
    
    async def extract_risks_from_documents(
        self, 
        documents: List[Dict[str, Any]], 
        question_topic: str
    ) -> List[Risk]:
        """Извлекает риски из списка документов"""
        all_risks = []
        
        # Обрабатываем документы батчами
        batch_size = 4  # Можно вынести в конфиг
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_risks = await self._extract_risks_from_batch(batch, question_topic)
            all_risks.extend(batch_risks)
        
        logger.info(f"Извлечено {len(all_risks)} рисков из {len(documents)} документов")
        return all_risks
    
    async def _extract_risks_from_batch(
        self, 
        documents: List[Dict[str, Any]], 
        question_topic: str
    ) -> List[Risk]:
        """Извлекает риски из батча документов"""
        batch_content = "\n\n".join([
            f"Документ: {doc.get('name', 'Unknown')}\n{doc.get('content', '')}"
            for doc in documents
        ])
        
        try:
            # 1. Проверка входных данных
            if not batch_content.strip():
                logger.error("Получен пустой контент документов")
                return []
                
            # 2. Подготовка входных данных
            input_data = {
                "documents_content": batch_content[:2000],
                "question_topic": question_topic
            }
            
            # 3. Выполнение цепочки
            logger.debug("Запуск цепочки извлечения рисков...")
            response = await self._risk_extraction_chain.ainvoke(input_data)
            
            if response is None:
                logger.error("LLM вернул None в ответе")
                return []
                
            logger.debug(f"Получен ответ длиной {len(response)} символов")
            
            # 4. Извлечение JSON
            risks_json = self.extractor.extract_json_sync(response)
            
            if not risks_json or "risks" not in risks_json:
                logger.warning(f"Не удалось извлечь JSON с рисками. Ответ: {response[:500]}...")
                return []
                
            # 5. Создание объектов Risk
            risks = []
            for risk_data in risks_json["risks"]:
                try:
                    risk_data = self._enrich_risk_data(risk_data, documents)
                    risk = Risk(**risk_data)
                    risks.append(risk)
                except Exception as e:
                    logger.warning(f"Ошибка создания Risk: {e}\nДанные: {risk_data}")
                    continue
                    
            logger.success(f"Успешно извлечено {len(risks)} рисков из батча")
            return risks
            
        except Exception as e:
            logger.error(f"Критическая ошибка при обработке батча: {str(e)}", exc_info=True)
            return []

    
    def _enrich_risk_data(self, risk_data: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Дополняет данные риска недостающими полями"""
        # Нормализация категории
        if "category" in risk_data:
            category_mapping = {
                "Операционный риск": "Операционный",
                "Аналитический риск": "Операционный",
                "Стратегический риск": "Операционный",
                # Добавьте другие маппинги по необходимости
            }
            risk_data["category"] = category_mapping.get(risk_data["category"], risk_data["category"])
    
   
        # Устанавливаем ID если его нет
        if "id" not in risk_data:
            risk_data["id"] = str(uuid.uuid4())
        
        # Устанавливаем дату создания
        if "created_at" not in risk_data:
            risk_data["created_at"] = datetime.now().isoformat()
        
        # Устанавливаем источник документа если его нет
        if "source_document" not in risk_data and documents:
            risk_data["source_document"] = documents[0].get("name", "Unknown")
        
        # Устанавливаем тип по умолчанию если его нет
        if "type" not in risk_data:
            risk_data["type"] = "Риск"
        
        # Устанавливаем обоснование по умолчанию если его нет
        if "justification" not in risk_data:
            risk_data["justification"] = "Автоматически определено системой"
        
        # Устанавливаем релевантность по умолчанию если её нет
        if "relevance" not in risk_data:
            risk_data["relevance"] = "Универсальный для любой компании"
        
        # Устанавливаем рекомендации по умолчанию если их нет
        if "recommendations" not in risk_data:
            risk_data["recommendations"] = ["Требуется дополнительный анализ для формирования рекомендаций"]
        
         # Остальные поля...
        if "category" not in risk_data:
            risk_data["category"] = "Операционный"
        
        # Устанавливаем серьезность по умолчанию если её нет
        if "severity" not in risk_data:
            risk_data["severity"] = "Средний"
        
        # Устанавливаем вероятность по умолчанию если её нет
        if "probability" not in risk_data:
            risk_data["probability"] = "Средняя"
        
        return risk_data
    
    async def extract_risks_from_single_document(
        self, 
        document: Dict[str, Any], 
        question_topic: str
    ) -> List[Risk]:
        """Извлекает риски из одного документа"""
        return await self._extract_risks_from_batch([document], question_topic)
