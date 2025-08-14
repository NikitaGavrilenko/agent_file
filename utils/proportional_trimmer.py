import re
from typing import List, Union
from loguru import logger


class ProportionalStringTrimmer:
    """
    Умный обрезчик текста, который сохраняет пропорциональность важных частей
    при обрезке до заданного размера
    """
    
    def __init__(self, max_length: int = 30000):
        self.max_length = max_length
    
    def trim(self, texts: Union[str, List[str]]) -> Union[str, List[str]]:
        """
        Обрезает текст или список текстов до максимальной длины
        
        Args:
            texts: Строка или список строк для обрезки
            
        Returns:
            Обрезанный текст или список обрезанных текстов
        """
        if isinstance(texts, str):
            return self._trim_single_text(texts)
        elif isinstance(texts, list):
            return self._trim_text_list(texts)
        else:
            logger.warning(f"Неподдерживаемый тип данных: {type(texts)}")
            return texts
    
    def _trim_single_text(self, text: str) -> str:
        """
        Обрезает одну строку текста
        """
        if len(text) <= self.max_length:
            return text
        
        # Пытаемся обрезать по предложениям
        sentences = self._split_into_sentences(text)
        result = ""
        
        for sentence in sentences:
            if len(result + sentence) <= self.max_length:
                result += sentence
            else:
                break
        
        if not result:
            # Если не удалось обрезать по предложениям, обрезаем по словам
            result = self._trim_by_words(text)
        
        return result.strip()
    
    def _trim_text_list(self, texts: List[str]) -> List[str]:
        """
        Обрезает список текстов, сохраняя пропорциональность
        """
        if not texts:
            return texts
        
        total_length = sum(len(text) for text in texts)
        
        if total_length <= self.max_length:
            return texts
        
        # Вычисляем пропорцию для каждого текста
        trimmed_texts = []
        remaining_length = self.max_length
        
        for text in texts:
            if remaining_length <= 0:
                break
            
            # Вычисляем пропорциональную длину для этого текста
            proportional_length = int((len(text) / total_length) * self.max_length)
            proportional_length = min(proportional_length, remaining_length)
            
            if proportional_length <= 0:
                continue
            
            # Обрезаем текст до пропорциональной длины
            trimmed_text = self._trim_to_length(text, proportional_length)
            trimmed_texts.append(trimmed_text)
            
            remaining_length -= len(trimmed_text)
        
        return trimmed_texts
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Разбивает текст на предложения
        """
        # Используем регулярное выражение для разбиения по предложениям
        sentence_pattern = r'[^.!?]+[.!?]+'
        sentences = re.findall(sentence_pattern, text)
        
        # Если регулярное выражение не сработало, разбиваем по точкам
        if not sentences:
            sentences = [s.strip() + '.' for s in text.split('.') if s.strip()]
        
        return sentences
    
    def _trim_by_words(self, text: str) -> str:
        """
        Обрезает текст по словам до максимальной длины
        """
        words = text.split()
        result = ""
        
        for word in words:
            if len(result + word + ' ') <= self.max_length:
                result += word + ' '
            else:
                break
        
        return result.strip()
    
    def _trim_to_length(self, text: str, max_length: int) -> str:
        """
        Обрезает текст до заданной длины, пытаясь сохранить целостность
        """
        if len(text) <= max_length:
            return text
        
        # Пытаемся обрезать по предложениям
        sentences = self._split_into_sentences(text)
        result = ""
        
        for sentence in sentences:
            if len(result + sentence) <= max_length:
                result += sentence
            else:
                break
        
        if not result:
            # Если не удалось обрезать по предложениям, обрезаем по словам
            result = self._trim_by_words(text)
            if len(result) > max_length:
                result = result[:max_length].rsplit(' ', 1)[0]
        
        return result.strip()
    
    def trim_until_think_tag(self, text: str) -> str:
        """
        Обрезает часть вывода до тега </think> (включая сам тег)
        """
        pattern = r'^.*?</think>\s*'
        result = re.sub(pattern, '', text, flags=re.DOTALL)
        return result if result else text
    
    def extract_think_content(self, text: str) -> str:
        """
        Извлекает содержимое тегов <think> из ответа модели
        """
        pattern = r'<think>(.*?)</think>'
        matches = re.findall(pattern, text, flags=re.DOTALL)
        
        if matches:
            return matches[0].strip()
        else:
            return ""
