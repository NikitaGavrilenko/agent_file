from dataclasses import dataclass, field
from typing import List, Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from loguru import logger

from models.risk import Risk, RelevanceType
from utils.json_extractor import Extractor


@dataclass
class RelevanceAnalyzer:
    """Класс для анализа релевантности рисков и ошибок"""
    
    llm: BaseChatModel
    extractor: Extractor
    
    _relevance_analysis_chain: Runnable[dict, str] = field(init=False)
    
    def __post_init__(self):
        # Загружаем промпт для анализа релевантности
        prompt_content = self._load_prompt("relevance_analysis")
        relevance_template = ChatPromptTemplate.from_messages([
            ("system", prompt_content)
        ])
        
        self._relevance_analysis_chain = relevance_template | self.llm | StrOutputParser()
    
    def _load_prompt(self, prompt_name: str) -> str:
        """Загружает промпт из файла"""
        try:
            import os

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prompt_path = os.path.join(project_root, 'promts', f"{prompt_name}.md")
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Промпт {prompt_name} не найден, используем базовый")
            return self._get_base_prompt()
    
    def _get_base_prompt(self) -> str:
        """Возвращает базовый промпт если файл не найден"""
        return """
        Ты - эксперт по определению релевантности рисков и ошибок. Определи тип релевантности для каждого элемента.
        
        Типы релевантности:
        - "Релевантен к сделке" - связан с конкретными условиями сделки, договорами, регулятором
        - "Релевантен к продукту" - связан с конкретными продуктами (ОСАГО, КАСКО, системы)
        - "Релевантен к документации" - связан с документами, согласованиями, лимитами
        - "Универсальный для любой компании" - общие угрозы, применимые к любой компании
        - "Нерелевантный" - нет привязки к сделке/продукту/документации
        
        Верни результат в формате JSON с полем "relevance_analysis".
        """
    
    async def analyze_relevance(self, risks: List[Risk]) -> List[Risk]:
        """Анализирует релевантность для списка рисков и ошибок"""
        if not risks:
            return risks
        
        try:
            # Анализируем релевантность для каждого риска/ошибки
            for risk in risks:
                relevance = await self._determine_relevance(risk)
                risk.relevance = relevance
                logger.debug(f"Определена релевантность для {risk.id}: {relevance}")
            
            logger.info(f"Проанализирована релевантность для {len(risks)} элементов")
            return risks
            
        except Exception as e:
            logger.error(f"Ошибка при анализе релевантности: {e}")
            return risks
    
    async def _determine_relevance(self, risk: Risk) -> RelevanceType:
        """Определяет релевантность для конкретного риска или ошибки"""
        try:
            # Анализируем текст на ключевые слова
            relevance = self._analyze_by_keywords(risk.description, risk.justification)
            if relevance:
                return relevance
            
            # Если не удалось определить по ключевым словам, используем LLM
            response = await self._relevance_analysis_chain.ainvoke({
                "risk_description": risk.description,
                "risk_justification": risk.justification,
                "risk_category": risk.category.value
            })
            
            # Извлекаем результат
            response = self.extractor.trim_think(response)
            result = self.extractor.extract_json_sync(response)
            
            if result and "relevance" in result:
                relevance_str = result["relevance"]
                return self._map_relevance_string(relevance_str)
            
            # Возвращаем универсальный тип по умолчанию
            return RelevanceType.UNIVERSAL
            
        except Exception as e:
            logger.warning(f"Не удалось определить релевантность для {risk.id}: {e}")
            return RelevanceType.UNIVERSAL
    
    def _analyze_by_keywords(self, description: str, justification: str) -> RelevanceType:
        """Анализирует релевантность по ключевым словам"""
        text = f"{description} {justification}".lower()
        
        # Релевантность к сделке
        deal_keywords = ["договор", "сделка", "регулятор", "предписание", "поставщик", "цб", "штраф"]
        if any(keyword in text for keyword in deal_keywords):
            return RelevanceType.DEAL_RELEVANT
        
        # Релевантность к продукту
        product_keywords = ["осаго", "каско", "система", "функционал", "продукт", "jarvisx", "ас авто"]
        if any(keyword in text for keyword in product_keywords):
            return RelevanceType.PRODUCT_RELEVANT
        
        # Релевантность к документации
        doc_keywords = ["согласование", "документ", "лимит", "дублирование", "таблица", "обоснование"]
        if any(keyword in text for keyword in doc_keywords):
            return RelevanceType.DOCUMENTATION_RELEVANT
        
        # Универсальный
        universal_keywords = ["закон", "контрагент", "обязательства", "законодательство"]
        if any(keyword in text for keyword in universal_keywords):
            return RelevanceType.UNIVERSAL
        
        return None
    
    def _map_relevance_string(self, relevance_str: str) -> RelevanceType:
        """Преобразует строку релевантности в enum"""
        relevance_str = relevance_str.lower().strip()
        
        if "сделке" in relevance_str or "сделка" in relevance_str:
            return RelevanceType.DEAL_RELEVANT
        elif "продукту" in relevance_str or "продукт" in relevance_str:
            return RelevanceType.PRODUCT_RELEVANT
        elif "документации" in relevance_str or "документ" in relevance_str:
            return RelevanceType.DOCUMENTATION_RELEVANT
        elif "универсальный" in relevance_str or "любой компании" in relevance_str:
            return RelevanceType.UNIVERSAL
        elif "нерелевантный" in relevance_str:
            return RelevanceType.NOT_RELEVANT
        else:
            return RelevanceType.UNIVERSAL
