import asyncio
import re
from typing import List, Generator, AsyncGenerator, TypeVar, Awaitable, Any
from loguru import logger
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


T = TypeVar('T')


class TextProcessor:
    """Улучшенный класс для обработки и группировки текста с поддержкой больших документов"""
    
    def __init__(self, max_chars_per_chunk: int = 30000, batch_size: int = 4):
        self.max_chars_per_chunk = max_chars_per_chunk
        self.batch_size = batch_size
        
        # Инициализируем сплиттер для больших документов
        self.splitter = RecursiveCharacterTextSplitter(
            separators=[".", "?", "!", "|", "\n\n", "\n", " "],
            chunk_size=max_chars_per_chunk,
            chunk_overlap=0,
            is_separator_regex=False,
        )
    
    def process_documents(self, documents: List[Document]) -> List[Document]:
        """
        Обрабатывает документы, разделяя большие и группируя маленькие
        
        Args:
            documents: Список документов для обработки
            
        Returns:
            Список обработанных чанков документов
        """
        long_docs, short_docs = [], []
        
        # Разделяем документы на большие и маленькие
        for doc in documents:
            if self.splitter._length_function(doc.page_content.strip()) > self.max_chars_per_chunk:
                long_docs.append(doc)
            else:
                short_docs.append(doc)
        
        # Разбиваем большие документы на чанки
        long_chunks = self.splitter.split_documents(documents=long_docs)
        
        # Группируем маленькие документы
        short_chunks = []
        if short_docs:
            # Форматируем маленькие документы
            formatted_short_docs = []
            for doc in short_docs:
                formatted_content = f"==================== ДОКУМЕНТ: {doc.metadata.get('name', doc.metadata.get('source', 'Неизвестно'))} ====================\n\n{doc.page_content.strip()}"
                formatted_short_docs.append(formatted_content)
            
            # Группируем в чанки
            short_chunks = self._merge_splits(formatted_short_docs, separator="\n")
            short_chunks = [Document(page_content=chunk, metadata=doc.metadata) for chunk in short_chunks]
        
        return long_chunks + short_chunks
    
    def _merge_splits(self, splits: List[str], separator: str = "\n") -> List[str]:
        """
        Объединяет маленькие сплиты в чанки оптимального размера
        """
        merged_chunks = []
        current_chunk = []
        current_length = 0
        
        for split in splits:
            split_length = len(split)
            
            if current_length + split_length <= self.max_chars_per_chunk:
                current_chunk.append(split)
                current_length += split_length
            else:
                if current_chunk:
                    merged_chunks.append(separator.join(current_chunk))
                current_chunk = [split]
                current_length = split_length
        
        if current_chunk:
            merged_chunks.append(separator.join(current_chunk))
        
        return merged_chunks
    
    def group_texts(self, texts: List[str], max_chars_per_chunk: int = None) -> List[List[str]]:
        """
        Группирует тексты в чанки по размеру для предотвращения переполнения контекста модели
        """
        if max_chars_per_chunk is None:
            max_chars_per_chunk = self.max_chars_per_chunk
            
        grouped_chunks: List[List[str]] = []
        current_chunk = []
        current_len = 0
        
        for text in texts:
            if current_len + len(text) <= max_chars_per_chunk:
                current_chunk.append(text)
                current_len += len(text)
            else:
                if current_chunk:
                    grouped_chunks.append(current_chunk)
                current_chunk = [text]
                current_len = len(text)
        
        if current_chunk:
            grouped_chunks.append(current_chunk)
            
        return grouped_chunks
    
    async def map_async_generator(
        self, 
        it: AsyncGenerator, 
        func: Awaitable[T], 
        batch_size: int = None
    ) -> List[T]:
        """
        Асинхронно обрабатывает генератор батчами с контролем нагрузки
        """
        if batch_size is None:
            batch_size = self.batch_size
            
        semaphore = asyncio.Semaphore(batch_size)
        
        async def task(input_item: Any) -> T:
            async with semaphore:
                return await func(input_item)
        
        results = []
        tasks = set()
        
        async for item in it:
            tasks.add(asyncio.create_task(task(item)))
            
            if len(tasks) >= batch_size:
                done, tasks = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for d in done:
                    results.append(d.result())
        
        if tasks:
            done, _ = await asyncio.wait(tasks)
            for d in done:
                results.append(d.result())
        
        return results
    
    def map_generator(
        self, 
        it: Generator, 
        func: Awaitable[T], 
        batch_size: int = None
    ) -> List[T]:
        """
        Обрабатывает генератор батчами с созданием нового event loop
        """
        if batch_size is None:
            batch_size = self.batch_size
            
        semaphore = asyncio.Semaphore(batch_size)
        
        async def task(input_item: Any) -> T:
            async with semaphore:
                return await func(input_item)
        
        results = []
        tasks = set()
        
        for item in it:
            tasks.add(asyncio.create_task(task(item)))
            
            if len(tasks) >= batch_size:
                # Создаем новый event loop для синхронного вызова
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    done, tasks = loop.run_until_complete(
                        asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    )
                    for d in done:
                        results.append(d.result())
                finally:
                    loop.close()
        
        if tasks:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                done, _ = loop.run_until_complete(asyncio.wait(tasks))
                for d in done:
                    results.append(d.result())
            finally:
                loop.close()
        
        return results
    
    def trim_text(self, text: str, max_length: int) -> str:
        """
        Умная обрезка текста до максимальной длины с сохранением целостности
        """
        if len(text) <= max_length:
            return text
        
        # Пытаемся обрезать по предложениям
        sentences = text.split('. ')
        result = ""
        
        for sentence in sentences:
            if len(result + sentence + '. ') <= max_length:
                result += sentence + '. '
            else:
                break
        
        if not result:
            # Если не удалось обрезать по предложениям, обрезаем по словам
            words = text.split()
            result = ""
            for word in words:
                if len(result + word + ' ') <= max_length:
                    result += word + ' '
                else:
                    break
        
        return result.strip()
    
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
    
    def extract_json_from_text(self, text: str) -> dict:
        """
        Извлекает JSON из текста ответа модели
        """
        # Ищем JSON между тройными обратными кавычками
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if match:
            try:
                import json
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.warning("Не удалось распарсить JSON из ответа модели")
        
        # Ищем JSON между фигурными скобками
        json_pattern = r'\{[\s\S]*?\}'
        match = re.search(json_pattern, text)
        
        if match:
            try:
                import json
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning("Не удалось распарсить JSON из ответа модели")
        
        return {}
    
    def trim_think_tags(self, text: str) -> str:
        """
        Обрезает теги <think> из ответа модели
        """
        # Убираем теги <think> и их содержимое
        think_pattern = r'<think>.*?</think>'
        text = re.sub(think_pattern, '', text, flags=re.DOTALL)
        
        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
