from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path


class Document(BaseModel):
    """Модель документа"""
    
    id: str = Field(description="Уникальный идентификатор документа")
    name: str = Field(description="Название документа")
    file_path: str = Field(description="Путь к файлу")
    file_type: str = Field(description="Тип файла (расширение)")
    file_size: int = Field(description="Размер файла в байтах")
    
    # Содержимое
    content: str = Field(description="Текстовое содержимое документа")
    
    # Метаданные
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные метаданные")
    
    # Статус обработки
    processed: bool = Field(default=False, description="Обработан ли документ")
    error: Optional[str] = Field(None, description="Ошибка при обработке")
    
    @classmethod
    def from_file(cls, file_path: str, content: str = "") -> "Document":
        """Создает документ из файла"""
        path = Path(file_path)
        return cls(
            id=str(hash(file_path)),
            name=path.name,
            file_path=file_path,
            file_type=path.suffix.lower(),
            file_size=path.stat().st_size if path.exists() else 0,
            content=content,
            metadata={
                "created_at": path.stat().st_ctime if path.exists() else None,
                "modified_at": path.stat().st_mtime if path.exists() else None,
            }
        )
    
    def __str__(self) -> str:
        return f"Document({self.name}, {self.file_type}, {len(self.content)} chars)"
