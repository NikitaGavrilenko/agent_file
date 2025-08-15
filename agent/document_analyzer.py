from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
import json
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from loguru import logger

from models.risk import Risk, RiskSeverity, RiskProbability, RiskCategory, RiskType, RelevanceType
from models.document import Document
from utils.file_loader import FileLoader
from utils.text_processor import TextProcessor
from utils.json_extractor import Extractor
from utils.file_manager import FileManager
from agent.risk_extractor import RiskExtractor
from agent.risk_deduplicator import RiskDeduplicator
from agent.report_generator import ReportGenerator
from agent.relevance_analyzer import RelevanceAnalyzer


@dataclass
class DocumentAnalyzer:
    """Улучшенный класс для анализа документов и выявления рисков с поддержкой больших документов"""
    
    llm: BaseChatModel
    file_loader: FileLoader
    text_processor: TextProcessor
    extractor: Extractor
    risk_extractor: RiskExtractor
    risk_deduplicator: RiskDeduplicator
    report_generator: ReportGenerator
    relevance_analyzer: RelevanceAnalyzer
    file_manager: FileManager
    
    # Конфигурация
    max_chars_per_chunk: int = 30000
    batch_size: int = 4
    
    async def analyze_documents(
        self, 
        folder_path: str, 
        question_topic: str
    ) -> Dict[str, Any]:
        """
        Основной метод анализа документов с улучшенной обработкой больших файлов
        
        Args:
            folder_path: Путь к папке с документами
            question_topic: Тема вопроса (например, "договор поставки", "сделка")
            
        Returns:
            Словарь с результатами анализа
        """
        start_time = datetime.now()
        logger.info(f"Начинаем анализ документов для темы: {question_topic}")
        
        try:
            # 1. Загружаем документы
            logger.info("Шаг 1: Загрузка документов")
            documents = await self._load_documents(folder_path)
            if not documents:
                raise ValueError(f"В папке {folder_path} не найдено поддерживаемых документов")
            
            # 2. Предобрабатываем документы (разбиваем большие на чанки)
            logger.info("Шаг 2: Предобработка документов")
            processed_documents = await self._preprocess_documents(documents)
            logger.info(f"Документы разбиты на {len(processed_documents)} чанков")
            
            # 3. Извлекаем риски
            logger.info("Шаг 3: Извлечение рисков")
            extracted_risks = await self._extract_risks_from_documents(processed_documents, question_topic)
            
            # 4. Дедублицируем риски
            logger.info("Шаг 4: Дедубликация рисков")
            deduplicated_risks = await self._deduplicate_risks(extracted_risks)
            
            # 5. Анализируем релевантность
            logger.info("Шаг 5: Анализ релевантности")
            risks_with_relevance = await self._analyze_relevance(deduplicated_risks)
            
            # 6. Генерируем отчет
            logger.info("Шаг 6: Генерация отчета")
            risk_report = await self._generate_risk_report(risks_with_relevance, question_topic)
            
            # 7. Формируем результат
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            result = {
                "question_topic": question_topic,
                "folder_path": folder_path,
                "processing_time_seconds": processing_time,
                "documents_analyzed": len(documents),
                "chunks_processed": len(processed_documents),
                "risks_found": len(extracted_risks),
                "risks_after_deduplication": len(deduplicated_risks),
                "risks_with_relevance": len(risks_with_relevance),
                "extracted_risks": [risk.model_dump() for risk in extracted_risks],
                "deduplicated_risks": [risk.model_dump() for risk in deduplicated_risks],
                "risks_with_relevance_data": [risk.model_dump() for risk in risks_with_relevance],
                "risk_report": risk_report,
                "analysis_summary": self._generate_analysis_summary(documents, processed_documents, extracted_risks, risks_with_relevance)
            }
            
            # 8. Сохраняем отчет в файлы
            logger.info("Шаг 7: Сохранение отчета")
            try:
                saved_report_path = self.file_manager.save_report(result, question_topic)
                if not Path(saved_report_path).exists():
                    logger.error("Файл отчета не был создан!")
                if saved_report_path:
                    result["saved_report_path"] = saved_report_path
                    logger.info(f"Отчет сохранен в: {saved_report_path}")
                else:
                    logger.warning("Не удалось сохранить отчет в файл")
            except Exception as e:
                logger.error(f"Ошибка при сохранении отчета: {e}")
            
            # 9. Сохраняем логи
            logger.info("Шаг 8: Сохранение логов")
            try:
                log_data = {
                    "analysis_session": {
                        "question_topic": question_topic,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "processing_time_seconds": processing_time,
                        "status": "completed"
                    },
                    "statistics": {
                        "documents_analyzed": len(documents),
                        "chunks_processed": len(processed_documents),
                        "risks_found": len(extracted_risks),
                        "risks_after_deduplication": len(deduplicated_risks),
                        "risks_with_relevance": len(risks_with_relevance)
                    },
                    "errors": []  # Здесь можно добавить информацию об ошибках
                }
                
                saved_log_path = self.file_manager.save_logs(log_data)
                if saved_log_path:
                    result["saved_log_path"] = saved_log_path
                    logger.info(f"Логи сохранены в: {saved_log_path}")
                else:
                    logger.warning("Не удалось сохранить логи в файл")
            except Exception as e:
                logger.error(f"Ошибка при сохранении логов: {e}")
            
            logger.info(f"Анализ завершен за {processing_time:.2f} секунд")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при анализе документов: {e}")
            raise
    
    async def _load_documents(self, folder_path: str) -> List[Document]:
        """Загружает документы из папки"""
        try:
            documents = await self.file_loader.load_documents_from_folder(folder_path)
            logger.info(f"Загружено {len(documents)} документов из папки {folder_path}")
            return documents
        except Exception as e:
            logger.error(f"Ошибка при загрузке документов: {e}")
            raise
    
    async def _preprocess_documents(self, documents: List[Document]) -> List[Document]:
        """Корректная предобработка документов с сохранением вашей модели"""
        try:
            processed_docs = []
            for doc in documents:
                # Создаем новый документ с обновленными данными
                processed_doc = Document(
                    id=doc.id,
                    name=doc.name,
                    file_path=doc.file_path,
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    content=doc.content,  # Основное содержимое
                    metadata={
                        **doc.metadata,
                        "processed": True,
                        "chunked": len(doc.content) > self.max_chars_per_chunk
                    }
                )
                processed_docs.append(processed_doc)
            
            logger.info(f"Документы предобработаны: {len(documents)} -> {len(processed_docs)}")
            return processed_docs
            
        except Exception as e:
            logger.error(f"Ошибка при предобработке документов: {e}")
            return documents
    
    async def _extract_risks_from_documents(self, documents: List[Document], question_topic: str) -> List[Risk]:
        """Корректное извлечение рисков из вашей модели Document"""
        try:
            doc_dicts = []
            for doc in documents:
                doc_dicts.append({
                    "name": doc.name,
                    "content": doc.content,  # Используем content вместо page_content
                    "file_path": doc.file_path,
                    "file_type": doc.file_type,
                    **doc.metadata  # Добавляем все метаданные
                })
            
            risks = await self._extract_risks_with_chunking(doc_dicts, question_topic)
            return risks
        except Exception as e:
            logger.error(f"Ошибка при извлечении рисков: {e}")
            raise

    
    async def _extract_risks_with_chunking(
        self, 
        documents: List[Dict], 
        question_topic: str
    ) -> List[Risk]:
        """
        Извлекает риски с поддержкой чанкинга для больших документов
        ИСПРАВЛЕНО: сохраняем оригинальные имена файлов
        """
        all_risks = []
        
        # Если документов немного, обрабатываем напрямую без группировки
        if len(documents) <= 10:
            # Обрабатываем документы напрямую, сохраняя их имена
            for doc in documents:
                doc_for_processing = {
                    "name": doc.get("name", "Unknown"),
                    "content": doc.get("content", ""),
                    "file_path": doc.get("file_path", "unknown"),
                    "file_type": doc.get("file_type", "unknown"),
                    "original_document": doc  # Сохраняем ссылку на оригинальный документ
                }
                
                try:
                    doc_risks = await self.risk_extractor.extract_risks_from_single_document(doc_for_processing, question_topic)
                    all_risks.extend(doc_risks)
                    logger.info(f"Из документа {doc.get('name', 'Unknown')} извлечено {len(doc_risks)} рисков")
                except Exception as e:
                    logger.warning(f"Ошибка при обработке документа {doc.get('name', 'Unknown')}: {e}")
                    continue
            
            return all_risks
        
        # Для большого количества документов используем группировку
        grouped_docs = self.text_processor.group_texts(
            [doc['content'] for doc in documents], 
            self.max_chars_per_chunk
        )
        
        logger.info(f"Документы сгруппированы в {len(grouped_docs)} групп для обработки")
        
        # Создаем мапинг контента к оригинальным документам
        content_to_doc = {}
        for doc in documents:
            content_to_doc[doc['content']] = doc
        
        for i, doc_group in enumerate(grouped_docs):
            logger.info(f"Обрабатываем группу документов {i+1}/{len(grouped_docs)}")
            
            # Создаем временные документы для группы, сохраняя связь с оригиналами
            temp_docs = []
            
            for j, content in enumerate(doc_group):
                # Находим оригинальный документ для этого контента
                original_doc = content_to_doc.get(content, {"name": "Unknown", "file_path": "unknown"})
                
                temp_docs.append({
                    "name": original_doc.get("name", "Unknown"),
                    "content": content,
                    "file_path": original_doc.get("file_path", "unknown"),
                    "file_type": original_doc.get("file_type", "unknown"),
                    "original_document": original_doc  # Передаем оригинальный документ
                })
            
            # Извлекаем риски из группы
            try:
                group_risks = await self.risk_extractor.extract_risks_from_documents(temp_docs, question_topic)
                all_risks.extend(group_risks)
                logger.info(f"Из группы {i+1} извлечено {len(group_risks)} рисков")
            except Exception as e:
                logger.warning(f"Ошибка при обработке группы {i+1}: {e}")
                continue
        
        return all_risks
    
    async def _deduplicate_risks(self, risks: List[Risk]) -> List[Risk]:
        """Дедублицирует риски"""
        try:
            if not risks:
                logger.info("Риски для дедубликации отсутствуют")
                return []
            
            dedup_risks = await self.risk_deduplicator.deduplicate_risks(risks, self.batch_size)
            logger.info(f"После дедубликации осталось {len(dedup_risks)} рисков из {len(risks)}")
            return dedup_risks
            
        except Exception as e:
            logger.error(f"Ошибка при дедубликации рисков: {e}")
            # Возвращаем исходные риски если дедубликация не удалась
            return risks
    
    async def _analyze_relevance(self, risks: List[Risk]) -> List[Risk]:
        """Анализирует релевантность рисков"""
        try:
            if not risks:
                logger.info("Риски для анализа релевантности отсутствуют")
                return []
            
            risks_with_relevance = await self.relevance_analyzer.analyze_relevance(risks)
            logger.info(f"После анализа релевантности осталось {len(risks_with_relevance)} рисков из {len(risks)}")
            return risks_with_relevance
            
        except Exception as e:
            logger.error(f"Ошибка при анализе релевантности рисков: {e}")
            # Возвращаем исходные риски если анализ релевантности не удался
            return risks
    
    async def _generate_risk_report(self, risks: List[Risk], question_topic: str) -> str:
        """Генерирует отчет по рискам"""
        if not risks:
            return "Риски не обнаружены"
        
        try:
            # Prepare the report data using the ReportGenerator's method
            report_data = self.report_generator._prepare_report_data(risks, question_topic)
            
            # Generate the report using the chain
            report = await self.report_generator._report_generation_chain.ainvoke(report_data)
            
            logger.info("Отчет по рискам успешно сгенерирован")
            return report
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета: {e}")
            return self.report_generator._generate_fallback_report(risks, question_topic)

    def _generate_analysis_summary(
        self, 
        original_documents: List[Document], 
        processed_documents: List[Document],
        extracted_risks: List[Risk], 
        final_risks: List[Risk]
    ) -> Dict[str, Any]:
        """Генерирует сводку анализа с информацией о чанкинге"""
        try:
            # Статистика по документам
            doc_stats = {
                "original_count": len(original_documents),
                "chunks_count": len(processed_documents),
                "chunking_ratio": len(processed_documents) / len(original_documents) if original_documents else 0
            }
            
            # Статистика по рискам
            risk_stats = {
                "total_extracted": len(extracted_risks),
                "final_count": len(final_risks),
                "reduction_ratio": len(final_risks) / len(extracted_risks) if extracted_risks else 0
            }
            
            # Анализ типов рисков
            risk_types = {}
            risk_relevance = {}
            
            for risk in final_risks:
                # Используем risk.type вместо risk.risk_type
                risk_type = risk.type.value if risk.type else "Не указан"
                risk_types[risk_type] = risk_types.get(risk_type, 0) + 1
                
                relevance = risk.relevance.value if risk.relevance else "Не указана"
                risk_relevance[relevance] = risk_relevance.get(relevance, 0) + 1
            
            return {
                "document_statistics": doc_stats,
                "risk_statistics": {
                    "types": risk_types,
                    "relevance": risk_relevance,
                    **risk_stats
                }
            }
        except Exception as e:
            logger.error(f"Ошибка при генерации сводки: {e}")
            return {"error": str(e)}
    
    async def analyze_single_document(
        self, 
        document_path: str, 
        question_topic: str
    ) -> Dict[str, Any]:
        """Анализирует один документ"""
        try:
            # Загружаем документ
            document = await self.file_loader.load_single_document(document_path)
            if not document:
                raise ValueError(f"Не удалось загрузить документ: {document_path}")
            
            # Извлекаем риски
            risks = await self.risk_extractor.extract_risks_from_single_document(
                {"name": document.name, "content": document.content}, 
                question_topic
            )
            
            # Генерируем отчет
            report = await self.report_generator.generate_risk_report(risks, question_topic)
            
            return {
                "question_topic": question_topic,
                "document_path": document_path,
                "risks_found": len(risks),
                "risks": [risk.model_dump() for risk in risks],
                "risk_report": report
            }
            
        except Exception as e:
            logger.error(f"Ошибка при анализе документа {document_path}: {e}")
            raise
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """Возвращает статус анализатора"""
        return {
            "status": "ready",
            "max_chars_per_chunk": self.max_chars_per_chunk,
            "batch_size": self.batch_size,
            "supported_formats": self.file_loader.supported_formats,
            "timestamp": datetime.now().isoformat()
        }


def create_analyzer() -> DocumentAnalyzer:
    """Создает и настраивает анализатор документов"""
    from config import config
    from langchain_openai import ChatOpenAI
    from utils.file_loader import FileLoader
    from utils.text_processor import TextProcessor
    from utils.json_extractor import Extractor
    from utils.file_manager import FileManager
    from agent.risk_extractor import RiskExtractor
    from agent.risk_deduplicator import RiskDeduplicator
    from agent.report_generator import ReportGenerator
    from agent.relevance_analyzer import RelevanceAnalyzer
    
    # Создаем LLM
    llm = ChatOpenAI(
        model=config.model_name,
        api_key=config.openai_api_key,
        base_url=config.openai_api_base,
        temperature=0.1,
        max_retries=config.max_retries
    )
    
    # Создаем компоненты
    file_loader = FileLoader()
    text_processor = TextProcessor(max_chars_per_chunk=config.max_chars_per_chunk)
    extractor = Extractor(llm)
    risk_extractor = RiskExtractor(llm, extractor, text_processor)
    risk_deduplicator = RiskDeduplicator(llm, extractor)
    report_generator = ReportGenerator(llm, extractor)
    relevance_analyzer = RelevanceAnalyzer(llm, extractor)
    file_manager = FileManager()
    
    # Создаем и возвращаем анализатор
    return DocumentAnalyzer(
        llm=llm,
        file_loader=file_loader,
        text_processor=text_processor,
        extractor=extractor,
        risk_extractor=risk_extractor,
        risk_deduplicator=risk_deduplicator,
        report_generator=report_generator,
        relevance_analyzer=relevance_analyzer,
        file_manager=file_manager,
        max_chars_per_chunk=config.max_chars_per_chunk,
        batch_size=config.batch_size
    )