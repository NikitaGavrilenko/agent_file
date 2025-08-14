import os
import sys
from pathlib import Path
from loguru import logger


def setup_logging(log_level: str = "INFO", log_to_file: bool = True):
    """
    Настраивает логирование для проекта
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Сохранять ли логи в файл
    """
    try:
        # Убираем стандартный обработчик
        logger.remove()
        
        # Добавляем обработчик для консоли
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True
        )
        
        # Добавляем обработчик для файла если нужно
        if log_to_file:
            # Создаем папку logs если её нет
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            # Создаем файл лога с ротацией
            log_file = logs_dir / "agent.log"
            
            logger.add(
                log_file,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level="DEBUG",  # В файл пишем все логи
                rotation="10 MB",  # Ротация при достижении 10MB
                retention="30 days",  # Храним логи 30 дней
                compression="zip",  # Сжимаем старые логи
                encoding="utf-8"
            )
            
            logger.info(f"Логирование настроено. Файл: {log_file}")
        else:
            logger.info("Логирование настроено только для консоли")
            
    except Exception as e:
        print(f"Ошибка при настройке логирования: {e}")
        # В случае ошибки используем базовое логирование
        logger.add(sys.stdout, level="INFO")


def get_logger(name: str = None):
    """
    Возвращает настроенный логгер
    
    Args:
        name: Имя логгера (обычно __name__)
        
    Returns:
        Настроенный логгер
    """
    if name:
        return logger.bind(name=name)
    return logger


def log_function_call(func_name: str, args: dict = None, result: any = None):
    """
    Декоратор для логирования вызовов функций
    
    Args:
        func_name: Имя функции
        args: Аргументы функции
        result: Результат функции
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Вызов функции {func_name} с аргументами: {args}, {kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Функция {func_name} завершена успешно")
                return result
            except Exception as e:
                logger.error(f"Ошибка в функции {func_name}: {e}")
                raise
        return wrapper
    return decorator


def log_async_function_call(func_name: str):
    """
    Декоратор для логирования асинхронных вызовов функций
    
    Args:
        func_name: Имя функции
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger.debug(f"Асинхронный вызов функции {func_name} с аргументами: {args}, {kwargs}")
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"Асинхронная функция {func_name} завершена успешно")
                return result
            except Exception as e:
                logger.error(f"Ошибка в асинхронной функции {func_name}: {e}")
                raise
        return wrapper
    return decorator


def log_performance(func_name: str):
    """
    Декоратор для логирования производительности функций
    
    Args:
        func_name: Имя функции
    """
    import time
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.debug(f"Начало выполнения {func_name}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"Функция {func_name} выполнена за {execution_time:.3f} сек")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Функция {func_name} завершилась с ошибкой за {execution_time:.3f} сек: {e}")
                raise
        return wrapper
    return decorator


def log_async_performance(func_name: str):
    """
    Декоратор для логирования производительности асинхронных функций
    
    Args:
        func_name: Имя функции
    """
    import time
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.debug(f"Начало выполнения асинхронной функции {func_name}")
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"Асинхронная функция {func_name} выполнена за {execution_time:.3f} сек")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Асинхронная функция {func_name} завершилась с ошибкой за {execution_time:.3f} сек: {e}")
                raise
        return wrapper
    return decorator


# Автоматическая настройка логирования при импорте модуля
if __name__ != "__main__":
    setup_logging()
