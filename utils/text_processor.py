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
        
        # ИСПРАВЛЕНО: Правильные настройки сплиттера
        self.splitter = RecursiveCharacterTextSplitter(
            separators=[
                "\n\n",    # Сначала разделяем по абзацам
                "\n",      # Потом по строкам
                ". ",      # Потом по предложениям (с пробелом!)
                "? ",      # Вопросительные предложения
                "! ",      # Восклицательные предложения
                "; ",      # Точка с запятой
                ": ",      # Двоеточие
                ", ",      # Запятые (осторожно с этим)
                " ",       # Пробелы
                ""         # В крайнем случае - любой символ
            ],
            chunk_size=max_chars_per_chunk,
            chunk_overlap=500,  # ДОБАВЛЕНО: перекрытие для сохранения контекста!
            is_separator_regex=False,
        )
        
        logger.info(f"TextProcessor инициализирован с chunk_size={max_chars_per_chunk}, overlap=500")
    
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
                logger.debug(f"Документ {doc.metadata.get('name', 'Unknown')} помечен как большой ({len(doc.page_content)} символов)")
            else:
                short_docs.append(doc)
        
        # Разбиваем большие документы на чанки
        long_chunks = []
        if long_docs:
            logger.info(f"Разбиваем {len(long_docs)} больших документов на чанки")
            long_chunks = self.splitter.split_documents(documents=long_docs)
            logger.info(f"Получено {len(long_chunks)} чанков из больших документов")
        
        # Группируем маленькие документы
        short_chunks = []
        if short_docs:
            logger.info(f"Группируем {len(short_docs)} маленьких документов")
            # Форматируем маленькие документы
            formatted_short_docs = []
            for doc in short_docs:
                # Убираем излишние переносы строк и пробелы
                cleaned_content = self.clean_text(doc.page_content.strip())
                formatted_content = f"==================== ДОКУМЕНТ: {doc.metadata.get('name', doc.metadata.get('source', 'Неизвестно'))} ====================\n\n{cleaned_content}"
                formatted_short_docs.append(formatted_content)
            
            # Группируем в чанки
            short_chunks = self._merge_splits(formatted_short_docs, separator="\n\n")
            short_chunks = [Document(page_content=chunk, metadata=short_docs[0].metadata) for chunk in short_chunks]
            logger.info(f"Получено {len(short_chunks)} чанков из маленьких документов")
        
        total_chunks = long_chunks + short_chunks
        logger.info(f"Итого чанков: {len(total_chunks)}")
        return total_chunks
    
    def _merge_splits(self, splits: List[str], separator: str = "\n\n") -> List[str]:
        """
        Объединяет маленькие сплиты в чанки оптимального размера
        ИСПРАВЛЕНО: учитываем overlap при группировке
        """
        merged_chunks = []
        current_chunk = []
        current_length = 0
        
        # Оставляем место для overlap
        effective_chunk_size = self.max_chars_per_chunk - 500  # Резерв для overlap
        
        for split in splits:
            split_length = len(split)
            
            if current_length + split_length <= effective_chunk_size:
                current_chunk.append(split)
                current_length += split_length + len(separator)  # +separator length
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
        ИСПРАВЛЕНО: учитываем overlap
        """
        if max_chars_per_chunk is None:
            max_chars_per_chunk = self.max_chars_per_chunk
        
        # Оставляем место для overlap
        effective_chunk_size = max_chars_per_chunk - 500
            
        grouped_chunks: List[List[str]] = []
        current_chunk = []
        current_len = 0
        
        for text in texts:
            text_len = len(text)
            
            # Если один текст больше effective_chunk_size, разбиваем его
            if text_len > effective_chunk_size:
                logger.warning(f"Текст длиной {text_len} превышает размер чанка, будет разбит")
                
                # Сохраняем текущий чанк если есть
                if current_chunk:
                    grouped_chunks.append(current_chunk)
                    current_chunk = []
                    current_len = 0
                
                # Разбиваем большой текст
                split_texts = self._split_large_text(text, effective_chunk_size)
                for split_text in split_texts:
                    grouped_chunks.append([split_text])
                
                continue
            
            if current_len + text_len <= effective_chunk_size:
                current_chunk.append(text)
                current_len += text_len
            else:
                if current_chunk:
                    grouped_chunks.append(current_chunk)
                current_chunk = [text]
                current_len = text_len
        
        if current_chunk:
            grouped_chunks.append(current_chunk)
        
        logger.info(f"Тексты сгруппированы в {len(grouped_chunks)} чанков")
        return grouped_chunks
    
    def _split_large_text(self, text: str, max_size: int) -> List[str]:
        """
        Разбивает большой текст на части с учетом overlap
        """
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        start = 0
        overlap = 500
        
        while start < len(text):
            end = start + max_size
            
            if end >= len(text):
                # Последний чанк
                chunks.append(text[start:])
                break
            
            # Ищем подходящее место для разреза (по предложению)
            cut_point = end
            for sep in [". ", ".\n", "! ", "!\n", "? ", "?\n"]:
                last_sep = text.rfind(sep, start, end)
                if last_sep > start + max_size // 2:  # Не слишком близко к началу
                    cut_point = last_sep + len(sep)
                    break
            
            chunks.append(text[start:cut_point])
            
            # Следующий чанк начинается с overlap
            start = max(cut_point - overlap, start + 1)
        
        return chunks
    
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
        ИСПРАВЛЕНО: не обрезаем в середине предложения
        """
        if len(text) <= max_length:
            return text
        
        # Пытаемся обрезать по предложениям
        sentences = re.split(r'(?<=[.!?])\s+', text)
        result = ""
        
        for sentence in sentences:
            if len(result + sentence + ' ') <= max_length:
                result += sentence + ' '
            else:
                break
        
        if not result or len(result) < max_length * 0.5:
            # Если не удалось обрезать по предложениям или результат слишком короткий
            # обрезаем по словам, но не в середине слова
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
        УЛУЧШЕНО: лучшая очистка с сохранением структуры
        """
        # Убираем множественные пробелы, но сохраняем структуру
        text = re.sub(r'[ \t]+', ' ', text)  # Множественные пробелы и табы
        
        # Убираем множественные переносы строк, но сохраняем абзацы
        text = re.sub(r'\n{3,}', '\n\n', text)  # Более 2 переносов -> 2
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Переносы с пробелами между
        
        # Убираем пробелы в начале и конце строк
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
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
    
    def get_chunk_info(self, text: str) -> dict:
        """
        Возвращает информацию о том, как будет разбит текст
        """
        if len(text) <= self.max_chars_per_chunk:
            return {
                "will_be_split": False,
                "total_length": len(text),
                "estimated_chunks": 1,
                "chunk_size": self.max_chars_per_chunk,
                "overlap": 500
            }
        
        # Прогнозируем количество чанков
        effective_size = self.max_chars_per_chunk - 500  # Учитываем overlap
        estimated_chunks = max(1, (len(text) - 500) // effective_size + 1)
        
        return {
            "will_be_split": True,
            "total_length": len(text),
            "estimated_chunks": estimated_chunks,
            "chunk_size": self.max_chars_per_chunk,
            "overlap": 500,
            "effective_chunk_size": effective_size
        }