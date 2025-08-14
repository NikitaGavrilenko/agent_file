#!/usr/bin/env python3
"""
Скрипт для запуска анализа документов в Jupyter notebook
"""

import asyncio
import nest_asyncio
import os
from pathlib import Path
from agent.document_analyzer import create_analyzer

# Применяем патч для Jupyter
nest_asyncio.apply()

def ensure_directories():
    """Создает необходимые папки если они не существуют"""
    for folder in ["documents", "reports", "logs"]:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            print(f"✅ Папка '{folder}' создана")
        else:
            print(f"✅ Папка '{folder}' уже существует")

async def analyze_documents_async(question_topic: str = "Анализ рисков и ошибок в документах"):
    """Асинхронная функция для анализа документов"""
    try:
        # Создаем анализатор
        analyzer = create_analyzer()
        
        # Запускаем анализ
        result = await analyzer.analyze_documents("documents", question_topic)
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_analysis(question_topic: str = "Анализ рисков и ошибок в документах"):
    """Функция для запуска анализа в Jupyter"""
    try:
        # Создаем необходимые папки
        print("📁 Проверяю наличие необходимых папок...")
        ensure_directories()
        
        # Запускаем асинхронную функцию
        result = asyncio.run(analyze_documents_async(question_topic))
        
        if result:
            print("\n✅ АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!")
            print(f"📊 Документов проанализировано: {result['documents_analyzed']}")
            print(f"⚠️  Элементов найдено: {result['risks_found']}")
            print(f"🔍 Элементов после дедубликации: {result['risks_after_deduplication']}")
            print(f"🎯 Элементов с релевантностью: {result['risks_with_relevance']}")
            print(f"⏱️  Время обработки: {result['processing_time_seconds']:.2f} сек")
            
            # Показываем информацию о сохраненных файлах
            if 'saved_report_path' in result:
                print(f"📁 Отчет сохранен в: {result['saved_report_path']}")
            if 'saved_log_path' in result:
                print(f"📋 Логи сохранены в: {result['saved_log_path']}")
            
            # Показываем статистику по типам
            if 'analysis_summary' in result and 'risk_statistics' in result['analysis_summary']:
                stats = result['analysis_summary']['risk_statistics']
                if 'types' in stats:
                    print(f"\n📋 РАЗБИВКА ПО ТИПАМ:")
                    for risk_type, count in stats['types'].items():
                        print(f"• {risk_type}: {count}")
                    
                if 'relevance' in stats:
                    print(f"\n🎯 РАЗБИВКА ПО РЕЛЕВАНТНОСТИ:")
                    for relevance, count in stats['relevance'].items():
                        print(f"• {relevance}: {count}")
            
            print(f"\n📁 Отчеты сохранены в папку 'reports'")
            print(f"📋 Логи сохранены в папку 'logs'")
            return result
        else:
            print("❌ Анализ не удался")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при запуске анализа: {e}")
        import traceback
        traceback.print_exc()
        return None

# Для использования в Jupyter notebook:
# from run_jupyter import run_analysis
# result = run_analysis("Мой вопрос по анализу")

if __name__ == "__main__":
    # Запуск из командной строки
    result = run_analysis()
