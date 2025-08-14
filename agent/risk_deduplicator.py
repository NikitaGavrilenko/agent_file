from dataclasses import dataclass, field
from typing import List, Dict, Any
# from itertools import batched  # Python 3.12+

from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from loguru import logger

from models.risk import Risk
from utils.json_extractor import Extractor


@dataclass
class RiskDeduplicator:
    """Класс для дедубликации рисков"""
    
    llm: BaseChatModel
    extractor: Extractor
    
    _deduplicator_step1_chain: Runnable[dict, str] = field(init=False)
    _deduplicator_step2_chain: Runnable[dict, str] = field(init=False)
    
    def __post_init__(self):
        # Загружаем промпты для дедубликации
        step1_prompt = self._load_prompt("dedub_step1_batch_prompt")
        step2_prompt = self._load_prompt("dedub_step2_prompt")
        
        # Создаем цепочки с правильными переменными
        self._deduplicator_step1_chain = (
            ChatPromptTemplate.from_messages([("system", step1_prompt)])
            .partial()  # Фиксируем любые статические переменные
            | self.llm 
            | StrOutputParser()
        )
        
        self._deduplicator_step2_chain = (
            ChatPromptTemplate.from_messages([("system", step2_prompt)])
            .partial()
            | self.llm 
            | StrOutputParser()
        )

    
    def _load_prompt(self, prompt_name: str) -> str:
        """Загружает промпт из файла"""
        try:
            import os

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prompt_path = os.path.join(project_root, 'promts', f"{prompt_name}.md")
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                # Проверяем, что промпт содержит нужные переменные
                if "{new_risks_batch}" not in content and "{all_risks}" not in content:
                    logger.warning(f"Промпт {prompt_name} не содержит ожидаемых переменных")
                return content
        except FileNotFoundError:
            logger.warning(f"Промпт {prompt_name} не найден, используем базовый")
            return self._get_base_deduplication_prompt()
        except Exception as e:
            logger.error(f"Ошибка при загрузке промпта {prompt_name}: {e}")
            return self._get_base_deduplication_prompt()

    
    def _get_base_deduplication_prompt(self) -> str:
        """Возвращает базовый промпт для дедубликации"""
        return """
        Ты - эксперт по дедубликации рисков. Сравни риски и убирай дубликаты.
        Верни результат в формате JSON с полем "risks", содержащим массив уникальных рисков.
        """
    
    async def deduplicate_risks(
        self, 
        risks: List[Risk], 
        batch_size: int = 1
    ) -> List[Risk]:
        """Дедублицирует список рисков"""
        if not risks:
            return []
        
        logger.info(f"Начинаем дедубликацию {len(risks)} рисков")
        
        # Первый шаг: сравнение с существующими рисками (если есть)
        risks_after_first_step = await self._first_step(risks, batch_size)
        
        # Второй шаг: дедубликация внутри списка
        dedup_risks = await self._second_step(risks_after_first_step)
        
        logger.info(f"После дедубликации осталось {len(dedup_risks)} рисков")
        return dedup_risks

    
    async def _first_step(
        self, 
        risks: List[Risk], 
        batch_size: int
    ) -> List[Risk]:
        """Первый шаг дедубликации: сравнение с существующими рисками"""
        result = []
        
        for i in range(0, len(risks), batch_size):
            risks_batch = risks[i:i + batch_size]
            
            try:
                res_str = await self._deduplicator_step1_chain.ainvoke({
                    "new_risks_batch": Risk.to_json_str(risks_batch)
                })
                
                res_str = self.extractor.trim_think(res_str)
                res_json = self.extractor.extract_json_sync(res_str)
                
                if res_json is None:
                    logger.warning(f"Не удалось дедублицировать батч {i}, пропускаем")
                    result.extend(risks_batch)
                    continue
                
                # Валидируем и добавляем риски
                for risk_data in res_json.get("risks", []):
                    try:
                        # Добавляем проверку типа данных
                        if not isinstance(risk_data, dict):
                            logger.warning(f"Некорректный формат данных риска: {type(risk_data)}")
                            continue
                            
                        risk = Risk(**risk_data)
                        result.append(risk)
                    except Exception as e:
                        logger.warning(f"Не удалось валидировать риск: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Ошибка при обработке батча {i}: {e}")
                result.extend(risks_batch)
        
        return result


    
    async def _second_step(self, risks: List[Risk]) -> List[Risk]:
        """Второй шаг дедубликации: убираем дубликаты внутри списка"""
        try:
            dedup_risks_str = await self._deduplicator_step2_chain.ainvoke({
                "all_risks": Risk.to_json_str(risks)
            })
            
            dedup_risks_str = self.extractor.trim_think(dedup_risks_str)
            dedup_risks_json = self.extractor.extract_json_sync(dedup_risks_str)
            
            if dedup_risks_json is None:
                logger.warning("Второй шаг дедубликации не смог предоставить валидный JSON")
                return risks
            
            # Валидируем и создаем объекты Risk
            dedup_risks = []
            for risk_data in dedup_risks_json.get("risks", []):
                try:
                    # Добавляем проверку типа данных
                    if not isinstance(risk_data, dict):
                        logger.warning(f"Некорректный формат данных риска: {type(risk_data)}")
                        continue
                        
                    risk = Risk(**risk_data)
                    dedup_risks.append(risk)
                except Exception as e:
                    logger.warning(f"Не удалось валидировать риск: {e}")
                    continue
            
            return dedup_risks
            
        except Exception as e:
            logger.error(f"Ошибка во втором шаге дедубликации: {e}")
            return risks


    
    def simple_deduplicate(self, risks: List[Risk]) -> List[Risk]:
        """Простая дедубликация по описанию (fallback)"""
        if not risks:
            return []
        
        seen_descriptions = set()
        unique_risks = []
        
        for risk in risks:
            description = getattr(risk, 'description', '').lower().strip()
            if description and description not in seen_descriptions:
                seen_descriptions.add(description)
                unique_risks.append(risk)
        
        return unique_risks
