from typing import Optional, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class RiskSeverity(str, Enum):
    """Уровень серьезности риска"""
    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"
    CRITICAL = "Критический"


class RiskProbability(str, Enum):
    """Вероятность реализации риска"""
    LOW = "Низкая"
    MEDIUM = "Средняя"
    HIGH = "Высокая"


class RiskCategory(str, Enum):
    """Категория риска"""
    FINANCIAL = "Финансовый"
    OPERATIONAL = "Операционный"
    LEGAL = "Юридический"
    TECHNOLOGICAL = "Технологический"
    REPUTATIONAL = "Репутационный"
    REGULATORY = "Регуляторный"
    DOCUMENTATION = "Документация"
    BUSINESS_PROCESS = "Бизнес-процесс"


class RiskType(str, Enum):
    """Тип: риск или ошибка"""
    RISK = "Риск"
    ERROR = "Ошибка"


class RelevanceType(str, Enum):
    """Тип релевантности"""
    DEAL_RELEVANT = "Релевантен к сделке"
    PRODUCT_RELEVANT = "Релевантен к продукту"
    DOCUMENTATION_RELEVANT = "Релевантен к документации"
    UNIVERSAL = "Универсальный для любой компании"
    NOT_RELEVANT = "Нерелевантный"


class Risk(BaseModel):
    """Модель риска или ошибки"""
    
    id: str = Field(description="Уникальный идентификатор")
    type: RiskType = Field(description="Тип: риск или ошибка")
    description: str = Field(description="Описание риска или ошибки")
    justification: str = Field(description="Обоснование классификации")
    relevance: RelevanceType = Field(description="Тип релевантности")
    recommendations: List[str] = Field(description="Список рекомендаций")
    
    # Основные характеристики
    category: RiskCategory = Field(description="Категория")
    severity: RiskSeverity = Field(description="Уровень серьезности")
    probability: RiskProbability = Field(description="Вероятность реализации")
    
    # Дополнительные поля
    impact: Optional[str] = Field(None, description="Описание возможного воздействия")
    mitigation: Optional[str] = Field(None, description="Рекомендации по снижению риска")
    source_document: Optional[str] = Field(None, description="Путь к документу")  
    source_page: Optional[str] = Field(None, description="Страница/раздел документа")
    
    # Метаданные
    created_at: Optional[str] = Field(None, description="Дата создания")
    tags: Optional[List[str]] = Field(default_factory=list, description="Теги для категоризации")
    
    # Дополнительные поля (для совместимости)
    model_config = {"extra": "allow"}
    
    @classmethod
    def to_json_str(cls, risks: List["Risk"]) -> str:
        """Конвертирует список рисков в JSON строку"""
        import json
        return json.dumps({"risks": [risk.model_dump() for risk in risks]}, ensure_ascii=False, indent=2)
    
    def __str__(self) -> str:
        return f"{self.type} ({self.category}): {self.description} ({self.severity}, {self.probability})"
    
    def get_formatted_output(self) -> str:
        """Возвращает отформатированный вывод для отчета"""
        output = f"{self.type.value}\n"
        output += f"**Обоснование:** {self.justification}\n"
        output += f"**Релевантность:** {self.relevance.value}\n"
        output += f"**Рекомендации:**\n"
        for rec in self.recommendations:
            output += f"- {rec}\n"
        return output
