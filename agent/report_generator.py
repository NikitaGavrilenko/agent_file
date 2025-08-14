from dataclasses import dataclass, field
from typing import List, Dict, Any

from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from loguru import logger

from models.risk import Risk
from utils.json_extractor import Extractor


@dataclass
class ReportGenerator:
    """Класс для генерации отчетов по рискам"""
    
    llm: BaseChatModel
    extractor: Extractor
    
    _report_generation_chain: Runnable[dict, str] = field(init=False)
    
    def __post_init__(self):
        # Загружаем промпт для генерации отчетов
        prompt_content = self._load_prompt("report_generation")
        report_template = ChatPromptTemplate.from_messages([
            ("system", prompt_content)
        ])
        
        self._report_generation_chain = report_template | self.llm | StrOutputParser()
    
    def _load_prompt(self, prompt_name: str) -> str:
        """Загружает промпт из файла"""
        try:
            import os

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prompt_path = os.path.join(project_root, 'promts', f"{prompt_name}.md")
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Промпт {prompt_name} не найден, используем базовый")
            return self._get_base_report_prompt()
    
    def _get_base_report_prompt(self) -> str:
        """Возвращает базовый промпт для генерации отчетов"""
        return """
        Ты - эксперт по составлению отчетов по рискам. Создай структурированный отчет на основе выявленных рисков.
        """
    
    async def _generate_risk_report(self, risks: List[Risk], question_topic: str) -> str:
        """Генерирует отчет по рискам"""
        if not risks:
            return "Риски не обнаружены"
        
        try:
            # Подготовка данных для отчета с правильными полями
            report_data = {
                "risks": [{
                    "description": risk.description,
                    "type": risk.type.value,
                    "category": risk.category.value,
                    "severity": risk.severity.value,
                    "probability": risk.probability.value,
                    "relevance": risk.relevance.value,
                    "justification": risk.justification,
                    "recommendations": risk.recommendations,
                    "source_document": risk.source_document,
                    "source_page": risk.source_page,  
                    "impact": risk.impact,
                    "mitigation": risk.mitigation
                } for risk in risks],
                "question_topic": question_topic,
                "risks_count": len(risks),
                "critical_count": sum(1 for r in risks if r.severity == RiskSeverity.CRITICAL),
                "high_count": sum(1 for r in risks if r.severity == RiskSeverity.HIGH),
                "medium_count": sum(1 for r in risks if r.severity == RiskSeverity.MEDIUM),
                "low_count": sum(1 for r in risks if r.severity == RiskSeverity.LOW)
            }
            
            report = await self.report_generator.generate_risk_report(report_data, question_topic)
            logger.info("Отчет по рискам успешно сгенерирован")
            return report
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета: {e}")
            return self._generate_fallback_report(risks, question_topic)
    
    def _prepare_report_data(self, risks: List[Risk], question_topic: str) -> Dict[str, Any]:
        """Подготавливает данные для генерации отчета с правильными именами переменных"""
        # Конвертируем риски в JSON
        risks_json = Risk.to_json_str(risks)
        
        # Подсчитываем статистику
        stats = self._calculate_risk_statistics(risks)
        
        return {
            "risks": risks_json,  # JSON строка с рисками
            "question_topic": question_topic,
            "risks_count": len(risks),  # Исправлено с risk_count на risks_count
            "critical_count": stats["critical"],
            "high_count": stats["high"],
            "medium_count": stats["medium"],
            "low_count": stats["low"]
        }
    
    def _calculate_risk_statistics(self, risks: List[Risk]) -> Dict[str, int]:
        """Подсчитывает статистику по рискам"""
        stats = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for risk in risks:
            severity = getattr(risk, 'severity', 'Средний')
            if severity == 'Критический':
                stats["critical"] += 1
            elif severity == 'Высокий':
                stats["high"] += 1
            elif severity == 'Средний':
                stats["medium"] += 1
            elif severity == 'Низкий':
                stats["low"] += 1
            else:
                stats["medium"] += 1  # По умолчанию
        
        return stats
    
    def _generate_fallback_report(self, risks: List[Risk], question_topic: str) -> str:
        """Создает простой отчет в случае ошибки генерации основного"""
        if not risks:
            return f"Для темы '{question_topic}' риски не обнаружены."
        
        report_lines = [
            f"Отчет по рискам для темы: {question_topic}",
            f"Всего обнаружено рисков: {len(risks)}",
            "\nДетализация рисков:"
        ]
        
        for i, risk in enumerate(risks, 1):
            report_lines.append(
                f"{i}. {risk.description}\n"
                f"   Тип: {risk.type.value}\n"
                f"   Категория: {risk.category.value}\n"
                f"   Серьезность: {risk.severity.value}\n"
                f"   Вероятность: {risk.probability.value}\n"
                f"   Релевантность: {risk.relevance.value}\n"
                f"   Обоснование: {risk.justification}\n"
                f"   Рекомендации: {', '.join(risk.recommendations)}\n"
                f"   Источник: {risk.source_document or 'Не указан'}"
                f"{f' (стр. {risk.source_page})' if risk.source_page else ''}"
            )
        
        return "\n".join(report_lines)
    
    def format_risks_for_display(self, risks: List[Risk]) -> str:
        """Форматирует риски для отображения"""
        if not risks:
            return "Риски не найдены"
        
        formatted = "## Детальный список рисков\n\n"
        
        for i, risk in enumerate(risks, 1):
            formatted += f"""
### {i}. {getattr(risk, 'description', 'Описание отсутствует')}

- **Категория**: {getattr(risk, 'category', 'Не указана')}
- **Серьезность**: {getattr(risk, 'severity', 'Не указана')}
- **Вероятность**: {getattr(risk, 'probability', 'Не указана')}
- **Воздействие**: {getattr(risk, 'impact', 'Не указано')}
- **Меры по снижению**: {getattr(risk, 'mitigation', 'Не указаны')}
- **Источник**: {getattr(risk, 'source_document', 'Не указан')}
- **Страница**: {getattr(risk, 'source_page', 'Не указана')}

---
"""
        
        return formatted
