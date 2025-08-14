#!/usr/bin/env python3
"""
Простой скрипт запуска агента анализа документов
"""

import os
import sys
from pathlib import Path

# Добавляем текущую папку в путь для импортов
sys.path.append(str(Path(__file__).parent))

def main():
    """Главная функция запуска"""
    print("🚀 Запуск агента анализа документов...")
    
    # Создаем необходимые папки
    print("\n📁 Создаю необходимые папки...")
    for folder in ["documents", "reports", "logs"]:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            print(f"✅ Папка '{folder}' создана")
        else:
            print(f"✅ Папка '{folder}' уже существует")
    
    # Проверяем наличие переменной окружения
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ ОШИБКА: Не установлен OPENAI_API_KEY")
        print("\nДля установки выполните в PowerShell:")
        print("$env:OPENAI_API_KEY = 'ваш_ключ_api'")
        print("\nИли создайте файл .env в корневой папке проекта:")
        print("OPENAI_API_KEY=ваш_ключ_api")
        return
    
    # Проверяем наличие документов
    documents = [f for f in os.listdir("documents") if f.lower().endswith(('.pdf', '.docx', '.pptx', '.txt'))]
    
    if not documents:
        print("\n📁 Папка 'documents' пуста")
        print("Добавьте документы для анализа и запустите скрипт снова")
        return
    
    print(f"\n📄 Найдено документов: {len(documents)}")
    for doc in documents:
        print(f"   - {doc}")
    
    print("\n" + "="*60)
    print("ВЫБЕРИТЕ РЕЖИМ РАБОТЫ")
    print("="*60)
    print("1. Быстрый анализ (автоматически)")
    print("2. Интерактивный режим")
    print("3. Выход")
    
    while True:
        choice = input("\nВыберите режим (1-3): ").strip()
        
        if choice == "1":
            # Быстрый анализ
            question_topic = input("Введите тему для анализа (например: 'договор поставки'): ").strip()
            if question_topic:
                print(f"\n🔍 Запускаю анализ документов для темы: '{question_topic}'")
                print("⏳ Это может занять несколько минут...")
                
                # Импортируем и запускаем анализ
                try:
                    from agent.document_analyzer import create_analyzer
                    import asyncio
                    
                    # Создаем анализатор и запускаем анализ
                    analyzer = create_analyzer()
                    result = asyncio.run(analyzer.analyze_documents("documents", question_topic))
                    
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
                                print(f"   - {risk_type}: {count}")
                        
                        if 'relevance' in stats:
                            print(f"\n🎯 РАЗБИВКА ПО РЕЛЕВАНТНОСТИ:")
                            for relevance, count in stats['relevance'].items():
                                print(f"   - {relevance}: {count}")
                    
                    print(f"\n📁 Отчеты сохранены в папку 'reports'")
                    print(f"📋 Логи сохранены в папку 'logs'")
                    
                except Exception as e:
                    print(f"\n❌ Ошибка при анализе: {e}")
                    print("Проверьте логи в папке 'logs'")
                
                break
            else:
                print("❌ Тема не указана")
                
        elif choice == "2":
            # Интерактивный режим
            print("\n🔄 Запуск интерактивного режима...")
            try:
                print("ℹ️  Интерактивный режим временно недоступен")
                print("Используйте режим 1 для быстрого анализа")
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
            break
            
        elif choice == "3":
            print("👋 До свидания!")
            break
            
        else:
            print("❌ Неверный выбор. Введите 1, 2 или 3")


if __name__ == "__main__":
    main()
