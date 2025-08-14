import json
import re
from typing import Any, Dict, Optional, Union
from loguru import logger


class EnhancedExtractor:
    """
    Улучшенный экстрактор для извлечения структурированных данных из ответов AI-моделей
    """
    
    def __init__(self):
        self.json_patterns = [
            r'```json\s*(.*?)\s*```',  # JSON в markdown блоках
            r'```\s*(.*?)\s*```',      # Код в markdown блоках
            r'\{[\s\S]*?\}',           # JSON между фигурными скобками
            r'\[[\s\S]*?\]',           # Массивы между квадратными скобками
        ]
    
    def extract_json_sync(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Синхронно извлекает JSON из текста
        """
        try:
            # Пытаемся найти JSON в тексте
            for pattern in self.json_patterns:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(json_str)
            
            # Если не нашли по паттернам, пытаемся найти любой JSON
            return self._find_any_json(text)
            
        except Exception as e:
            logger.warning(f"Не удалось извлечь JSON: {e}")
            return None
    
    def extract_json_async(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Асинхронно извлекает JSON из текста (для совместимости)
        """
        return self.extract_json_sync(text)
    
    def _find_any_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Ищет любой JSON в тексте
        """
        try:
            # Ищем начало JSON объекта
            start_idx = text.find('{')
            if start_idx == -1:
                return None
            
            # Ищем соответствующий закрывающий символ
            brace_count = 0
            end_idx = start_idx
            
            for i, char in enumerate(text[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break
            
            if brace_count == 0:
                json_str = text[start_idx:end_idx + 1]
                return json.loads(json_str)
            
        except Exception as e:
            logger.debug(f"Не удалось найти JSON: {e}")
        
        return None
    
    def trim_think(self, text: str) -> str:
        """
        Убирает теги <think> и их содержимое из ответа модели
        """
        # Убираем теги <think> и их содержимое
        think_pattern = r'<think>.*?</think>'
        text = re.sub(think_pattern, '', text, flags=re.DOTALL)
        
        # Убираем лишние пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def extract_router_decision(self, text: str) -> Optional[str]:
        """
        Извлекает решение роутера из ответа модели
        """
        # Ищем ключевые слова решения
        decision_patterns = [
            r'решение[:\s]+([^.\n]+)',
            r'выбор[:\s]+([^.\n]+)',
            r'маршрут[:\s]+([^.\n]+)',
            r'направление[:\s]+([^.\n]+)',
        ]
        
        for pattern in decision_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_risk_data(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Извлекает данные о рисках из текста
        """
        try:
            # Сначала пытаемся извлечь JSON
            json_data = self.extract_json_sync(text)
            if json_data:
                return json_data
            
            # Если JSON не найден, пытаемся извлечь структурированные данные
            risk_data = {}
            
            # Ищем описание риска
            description_match = re.search(r'описание[:\s]+([^.\n]+)', text, re.IGNORECASE)
            if description_match:
                risk_data['description'] = description_match.group(1).strip()
            
            # Ищем тип риска
            type_match = re.search(r'тип[:\s]+([^.\n]+)', text, re.IGNORECASE)
            if type_match:
                risk_data['type'] = type_match.group(1).strip()
            
            # Ищем вероятность
            probability_match = re.search(r'вероятность[:\s]+([^.\n]+)', text, re.IGNORECASE)
            if probability_match:
                risk_data['probability'] = probability_match.group(1).strip()
            
            # Ищем влияние
            impact_match = re.search(r'влияние[:\s]+([^.\n]+)', text, re.IGNORECASE)
            if impact_match:
                risk_data['impact'] = impact_match.group(1).strip()
            
            return risk_data if risk_data else None
            
        except Exception as e:
            logger.warning(f"Не удалось извлечь данные о рисках: {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """
        Очищает текст от лишних символов и форматирования
        """
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Убираем множественные переносы строк
        text = re.sub(r'\n+', '\n', text)
        
        # Убираем лишние пробелы в начале и конце
        text = text.strip()
        
        return text
    
    def extract_list_items(self, text: str) -> list[str]:
        """
        Извлекает элементы списка из текста
        """
        # Ищем маркированные списки
        bullet_pattern = r'^[\s]*[-*•]\s+(.+)$'
        bullet_items = re.findall(bullet_pattern, text, re.MULTILINE)
        
        # Ищем нумерованные списки
        number_pattern = r'^[\s]*\d+[\.\)]\s+(.+)$'
        number_items = re.findall(number_pattern, text, re.MULTILINE)
        
        # Ищем списки с двоеточием
        colon_pattern = r'^[\s]*([^:]+):\s*(.+)$'
        colon_items = re.findall(colon_pattern, text, re.MULTILINE)
        
        all_items = bullet_items + number_items + [': '.join(item) for item in colon_items]
        
        # Очищаем элементы
        cleaned_items = [item.strip() for item in all_items if item.strip()]
        
        return cleaned_items
