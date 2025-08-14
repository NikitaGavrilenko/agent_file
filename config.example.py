import os
from typing import Optional
from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Конфигурация агента анализа документов"""
    
    # OpenAI настройки
    openai_api_key: str = "YOUR_API_KEY_HERE"  # Замените на ваш API ключ
    openai_api_base: str = "YOUR_API_BASE_URL_HERE"  # Замените на ваш URL API
    model_name: str = "Qwen3-32B-AWQ"
    
    # Настройки обработки больших документов
    max_chars_per_chunk: int = 30000      # Максимальный размер чанка
    chunk_overlap: int = 0                # Перекрытие между чанками
    min_chunk_size: int = 1000            # Минимальный размер чанка
    batch_size: int = 4                   # Размер батча для обработки
    max_retries: int = 3                  # Количество попыток при ошибках
    
    # Настройки логирования
    log_level: str = "INFO"
    
    # Настройки агента
    think_mode: bool = True
    recursion_limit: int = 10
    
    # Настройки обработки документов
    separators: list[str] = [".", "?", "!", "|", "\n\n", "\n", " "]
    enable_smart_chunking: bool = True    # Включить умное разбиение
    enable_proportional_trimming: bool = True  # Включить пропорциональную обрезку


class FileProcessingConfig(BaseModel):
    """Конфигурация обработки файлов"""
    
    # Поддерживаемые форматы
    supported_formats: list[str] = [".pdf", ".docx", ".pptx", ".txt"]
    
    # Максимальный размер файла (в байтах)
    max_file_size: int = 100 * 1024 * 1024  # 100MB (увеличено для больших документов)
    
    # Временная папка для загрузки
    temp_folder: str = "./temp_uploads"
    
    # Настройки чанкинга
    enable_document_chunking: bool = True
    preserve_document_structure: bool = True


# Глобальная конфигурация
config = AgentConfig()
file_config = FileProcessingConfig()


# Инструкции по настройке:
# 1. Скопируйте этот файл как config.py
# 2. Замените YOUR_API_KEY_HERE на ваш реальный API ключ
# 3. Замените YOUR_API_BASE_URL_HERE на ваш URL API
# 4. НИКОГДА не коммитьте config.py с реальными ключами!
# 5. Используйте переменные окружения для продакшена:
#    export OPENAI_API_KEY="ваш_ключ"
#    export OPENAI_API_BASE="ваш_url"
