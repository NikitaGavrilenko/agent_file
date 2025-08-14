import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger


class FileManager:
    """Утилита для управления файлами, папками и сохранения отчетов"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.reports_dir = self.base_path / "reports"
        self.logs_dir = self.base_path / "logs"
        self.documents_dir = self.base_path / "documents"
        self._ensure_directories()  # Явное создание папок при инициализации
        
            
    def _ensure_directories(self):
        """Создает необходимые папки если они не существуют"""
        for directory in [self.reports_dir, self.logs_dir, self.documents_dir]:
            directory.mkdir(exist_ok=True)
            logger.info(f"Папка {directory} готова к использованию")
    
    def save_report(self, report_data: Dict[str, Any], question_topic: str) -> str:
        """
        Сохраняет отчет в папку reports
        
        Args:
            report_data: Данные отчета
            question_topic: Тема анализа
            
        Returns:
            Путь к сохраненному файлу
        """
        try:
            # Создаем имя файла с временной меткой
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = "".join(c for c in question_topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_topic = safe_topic.replace(' ', '_')[:50]  # Ограничиваем длину
            
            filename = f"report_{safe_topic}_{timestamp}.json"
            filepath = self.reports_dir / filename
            
            # Сохраняем JSON отчет
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            # Создаем текстовый отчет
            text_filename = f"report_{safe_topic}_{timestamp}.txt"
            text_filepath = self.reports_dir / text_filename
            
            with open(text_filepath, 'w', encoding='utf-8') as f:
                f.write(self._format_report_as_text(report_data))
            
            logger.info(f"Отчет сохранен в {filepath} и {text_filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении отчета: {e}")
            return ""
    
    def _format_report_as_text(self, report_data: Dict[str, Any]) -> str:
        """Форматирует отчет как читаемый текст"""
        lines = []
        
        # Заголовок
        lines.append("=" * 80)
        lines.append(f"ОТЧЕТ ПО АНАЛИЗУ РИСКОВ")
        lines.append(f"Тема: {report_data.get('question_topic', 'Не указана')}")
        lines.append(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")
        
        # Статистика
        lines.append("📊 СТАТИСТИКА АНАЛИЗА:")
        lines.append(f"   • Документов проанализировано: {report_data.get('documents_analyzed', 0)}")
        lines.append(f"   • Чанков обработано: {report_data.get('chunks_processed', 0)}")
        lines.append(f"   • Рисков найдено: {report_data.get('risks_found', 0)}")
        lines.append(f"   • После дедубликации: {report_data.get('risks_after_deduplication', 0)}")
        lines.append(f"   • С релевантностью: {report_data.get('risks_with_relevance', 0)}")
        lines.append(f"   • Время обработки: {report_data.get('processing_time_seconds', 0):.2f} сек")
        lines.append("")
        
        # Анализ по типам
        if 'analysis_summary' in report_data and 'risk_statistics' in report_data['analysis_summary']:
            stats = report_data['analysis_summary']['risk_statistics']
            
            if 'types' in stats:
                lines.append("📋 РАЗБИВКА ПО ТИПАМ:")
                for risk_type, count in stats['types'].items():
                    lines.append(f"   • {risk_type}: {count}")
                lines.append("")
            
            if 'relevance' in stats:
                lines.append("🎯 РАЗБИВКА ПО РЕЛЕВАНТНОСТИ:")
                for relevance, count in stats['relevance'].items():
                    lines.append(f"   • {relevance}: {count}")
                lines.append("")
        
        # Детализация рисков
        if 'risks_with_relevance_data' in report_data:
            lines.append("⚠️  ДЕТАЛИЗАЦИЯ РИСКОВ:")
            lines.append("")
            
            for i, risk in enumerate(report_data['risks_with_relevance_data'], 1):
                lines.append(f"{i}. {risk.get('description', 'Описание отсутствует')}")
                lines.append(f"   Тип: {risk.get('type', 'Не указан')}")
                lines.append(f"   Категория: {risk.get('category', 'Не указана')}")
                lines.append(f"   Серьезность: {risk.get('severity', 'Не указана')}")
                lines.append(f"   Вероятность: {risk.get('probability', 'Не указана')}")
                lines.append(f"   Релевантность: {risk.get('relevance', 'Не указана')}")
                lines.append(f"   Обоснование: {risk.get('justification', 'Не указано')}")
                
                recommendations = risk.get('recommendations', [])
                if recommendations:
                    lines.append(f"   Рекомендации:")
                    for rec in recommendations:
                        lines.append(f"     - {rec}")
                
                source_doc = risk.get('source_document', 'Не указан')
                source_page = risk.get('source_page', '')
                if source_page:
                    lines.append(f"   Источник: {source_doc} (стр. {source_page})")
                else:
                    lines.append(f"   Источник: {source_doc}")
                
                lines.append("")
        
        # Заключение
        lines.append("=" * 80)
        lines.append("Отчет сгенерирован автоматически системой анализа рисков")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_logs(self, log_data: Dict[str, Any], filename: str = None) -> str:
        """
        Сохраняет логи в папку logs
        
        Args:
            log_data: Данные логов
            filename: Имя файла (если не указано, генерируется автоматически)
            
        Returns:
            Путь к сохраненному файлу
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"analysis_log_{timestamp}.json"
            
            filepath = self.logs_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Логи сохранены в {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении логов: {e}")
            return ""
    
    def get_reports_list(self) -> List[str]:
        """Возвращает список всех отчетов"""
        try:
            reports = []
            for file in self.reports_dir.glob("*.json"):
                reports.append(str(file))
            return sorted(reports, reverse=True)  # Новые сначала
        except Exception as e:
            logger.error(f"Ошибка при получении списка отчетов: {e}")
            return []
    
    def get_logs_list(self) -> List[str]:
        """Возвращает список всех логов"""
        try:
            logs = []
            for file in self.logs_dir.glob("*.json"):
                logs.append(str(file))
            return sorted(logs, reverse=True)  # Новые сначала
        except Exception as e:
            logger.error(f"Ошибка при получении списка логов: {e}")
            return []
    
    def cleanup_old_files(self, max_files: int = 50):
        """
        Удаляет старые файлы, оставляя только последние max_files
        
        Args:
            max_files: Максимальное количество файлов для хранения
        """
        try:
            # Очистка отчетов
            reports = self.get_reports_list()
            if len(reports) > max_files:
                for old_report in reports[max_files:]:
                    try:
                        os.remove(old_report)
                        logger.info(f"Удален старый отчет: {old_report}")
                    except Exception as e:
                        logger.warning(f"Не удалось удалить старый отчет {old_report}: {e}")
            
            # Очистка логов
            logs = self.get_logs_list()
            if len(logs) > max_files:
                for old_log in logs[max_files:]:
                    try:
                        os.remove(old_log)
                        logger.info(f"Удален старый лог: {old_log}")
                    except Exception as e:
                        logger.warning(f"Не удалось удалить старый лог {old_log}: {e}")
                        
        except Exception as e:
            logger.error(f"Ошибка при очистке старых файлов: {e}")
    
    def get_directory_info(self) -> Dict[str, Any]:
        """Возвращает информацию о папках проекта"""
        try:
            info = {}
            
            for name, directory in [
                ("reports", self.reports_dir),
                ("logs", self.logs_dir),
                ("documents", self.documents_dir)
            ]:
                if directory.exists():
                    files = list(directory.glob("*"))
                    info[name] = {
                        "path": str(directory),
                        "exists": True,
                        "file_count": len(files),
                        "total_size": sum(f.stat().st_size for f in files if f.is_file())
                    }
                else:
                    info[name] = {
                        "path": str(directory),
                        "exists": False,
                        "file_count": 0,
                        "total_size": 0
                    }
            
            return info
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о папках: {e}")
            return {}
