import re
from typing import Optional, Dict, Any
from langchain_core.language_models import BaseChatModel
from loguru import logger


class Extractor:
    """Класс для извлечения и обработки JSON из текста"""
    
    # Паттерны для поиска JSON
    PATTERN_JSON_MD = re.compile(r"```json\s*({[\s\S]*?})\s*```")
    PATTERN_JSON = re.compile(r"\{[\s\S]*?\}")
    
    # Паттерны для работы с think тегами
    PATTERN_TRIM_THINK = re.compile(r"<think>.*?</think>\s*", flags=re.DOTALL)
    PATTERN_EXTRACT_THINK = re.compile(r"<think>(.*?)</think>", flags=re.DOTALL)
    
    def __init__(self, llm: Optional[BaseChatModel] = None):
        self.llm = llm
    
    @classmethod
    def extract_json_str_from_md(cls, text: str) -> Optional[str]:
        """Извлекает JSON из markdown блока"""
        if match := re.search(cls.PATTERN_JSON_MD, text):
            return match.group(1)
        return None
    
    @classmethod
    def extract_json_str(cls, text: str) -> Optional[str]:
        """Извлекает JSON из текста"""
        if match := re.search(cls.PATTERN_JSON, text):
            return match.group(0)
        return None
    
    @classmethod
    def trim_think(cls, text: str) -> str:
        """Убирает think теги из текста"""
        return re.sub(cls.PATTERN_TRIM_THINK, "", text)
    
    @classmethod
    def extract_think(cls, text: str) -> str:
        """Извлекает содержимое think тегов"""
        matches = re.findall(cls.PATTERN_EXTRACT_THINK, text)
        if matches:
            return matches[0].strip()
        return ""
    
    def extract_json_sync(self, text: str) -> Optional[Dict[str, Any]]:
        """Синхронно извлекает JSON из текста"""
        import json
        text = self.trim_think(text)
        # Сначала пробуем извлечь из markdown
        data_str = self.extract_json_str_from_md(text)
        
        # Если не получилось, ищем обычный JSON
        if data_str is None:
            data_str = self.extract_json_str(text)
        
        # Если все еще нет, используем весь текст
        if data_str is None:
            data_str = text
        
        try:
            return json.loads(data_str)
        except Exception as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return None
    
    async def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Асинхронно извлекает JSON из текста"""
        return self.extract_json_sync(text)
    
    def fix_json_sync(self, text: str) -> str:
        """Исправляет JSON с помощью LLM"""
        if not self.llm:
            logger.warning("LLM not available for JSON fixing")
            return text
        
        prompt = f"""
        В данной JSON структуре где-то есть ошибка, неправильно расставлены скобки или разделители.
        Проанализируй ТОЛЬКО СТРУКТУРУ JSON и исправь ошибку, при этом никак не изменяя содержимое полей или названия полей.
        Если ошибок нет, то верни исходный JSON без изменений. В твоём ответе должно содержаться ТОЛЬКО JSON и больше ничего.
        
        Вот JSON для исправления: {text}
        """
        
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Failed to fix JSON with LLM: {e}")
            return text
