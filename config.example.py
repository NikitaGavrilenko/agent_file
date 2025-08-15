import os
from typing import Optional
from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Конфигурация агента анализа документов"""
    
    # OpenAI настройки
    openai_api_key: str = "YOUR_API_KEY_HERE"  # Замените на ваш API ключ
    openai_api_base: str = "YOUR_API_BASE_URL_HERE"  # Замените на ваш URL API
    model_name: str = "Qwen3-32B-AWQ"
    
    # ИСПРАВЛЕННЫЕ настройки обработки больших документов
    max_chars_per_chunk: int = 30000      # Максимальный размер чанка
    chunk_overlap: int = 500              # ДОБАВЛЕНО: перекрытие между чанками
    min_chunk_size: int = 1000            # Минимальный размер чанка
    batch_size: int = 4                   # Размер батча для обработки
    max_retries: int = 3                  # Количество попыток при ошибках
    
    # Настройки логирования
    log_level: str = "INFO"
    
    # Настройки агента
    think_mode: bool = True
    recursion_limit: int = 10
    
    # УЛУЧШЕННЫЕ настройки обработки документов
    separators: list[str] = ["\n\n", "\n", ". ", "? ", "! ", "; ", ": ", " ", ""]
    enable_smart_chunking: bool = True    # Включить умное разбиение
    enable_proportional_trimming: bool = True  # Включить пропорциональную обрезку
    preserve_definitions: bool = True     # НОВОЕ: сохранять целостность определений
    preserve_sentences: bool = True       # НОВОЕ: не разрезать предложения


class FileProcessingConfig(BaseModel):
    """Конфигурация обработки файлов"""
    
    # Поддерживаемые форматы
    supported_formats: list[str] = [".pdf", ".docx", ".pptx", ".txt"]
    
    # Максимальный размер файла (в байтах)
    max_file_size: int = 100 * 1024 * 1024  # 100MB (увеличено для больших документов)
    
    # Временная папка для загрузки
    temp_folder: str = "./temp_uploads"
    
    # УЛУЧШЕННЫЕ настройки чанкинга
    enable_document_chunking: bool = True
    preserve_document_structure: bool = True
    smart_overlap: bool = True              # НОВОЕ: умное перекрытие
    context_preservation: bool = True       # НОВОЕ: сохранение контекста


# Глобальная конфигурация
config = AgentConfig()
file_config = FileProcessingConfig()


# НОВЫЕ РЕКОМЕНДАЦИИ ПО НАСТРОЙКЕ ДЛЯ ИСПРАВЛЕНИЯ ПРОБЛЕМ С НАРЕЗКОЙ:
# ===============================================================================
# 
# 1. РАЗМЕР ЧАНКА (max_chars_per_chunk):
#    - 30000 символов - хорошо для большинства документов
#    - Можно увеличить до 50000 для очень детальных документов
#    - Не рекомендуется менее 20000 - может потерять контекст
#
# 2. ПЕРЕКРЫТИЕ (chunk_overlap):
#    - 500 символов - минимум для сохранения определений
#    - 1000 символов - для документов с длинными определениями
#    - 2000 символов - для максимального сохранения контекста
#    - НЕ СТАВЬТЕ 0! Это главная причина обрывов определений
#
# 3. СЕПАРАТОРЫ (separators):
#    - ПОРЯДОК ВАЖЕН! Сначала абзацы, потом предложения
#    - ОБЯЗАТЕЛЬНО добавляйте пробел после знаков препинания
#    - Не ставьте точку первой - это разрежет все определения
#
# 4. ДЛЯ ЮРИДИЧЕСКИХ/ТЕХНИЧЕСКИХ ДОКУМЕНТОВ:
#    - Увеличьте chunk_overlap до 1000-2000
#    - Добавьте специальные разделители: ["\n\n", "\n", ".\n", ". ", ";\n", "; "]
#    - Включите preserve_definitions = True
#
# ===============================================================================

# Инструкции по настройке:
# 1. Скопируйте этот файл как config.py
# 2. Замените YOUR_API_KEY_HERE на ваш реальный API ключ
# 3. Замените YOUR_API_BASE_URL_HERE на ваш URL API
# 4. НИКОГДА не коммитьте config.py с реальными ключами!
# 5. Используйте переменные окружения для продакшена:
#    export OPENAI_API_KEY="ваш_ключ"
#    export OPENAI_API_BASE="ваш_url"
# 6. ВАЖНО: Настройте chunk_overlap для ваших документов!