"""
Modern ETL Pipeline with orchestration and monitoring
"""
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

try:
    from backend.extract import DataExtractor, DataSourceType
    from backend.transform import DataTransformer, DataQualityReport
    from backend.load import DataLoader, LoadDestination
    from backend.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    # Fallback imports
    import extract
    import transform
    import load_data


@dataclass
class ETLPipelineResult:
    """ETL pipeline execution result"""
    success: bool
    records_extracted: int
    records_transformed: int
    records_loaded: int
    records_valid: int
    records_invalid: int
    quality_score: float
    duration_seconds: float
    errors: List[str]
    quality_report: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "records_extracted": self.records_extracted,
            "records_transformed": self.records_transformed,
            "records_loaded": self.records_loaded,
            "records_valid": self.records_valid,
            "records_invalid": self.records_invalid,
            "quality_score": round(self.quality_score, 3),
            "duration_seconds": round(self.duration_seconds, 3),
            "errors": self.errors,
            "quality_report": self.quality_report
        }


class ETLPipeline:
    """Modern ETL pipeline orchestrator"""
    
    def __init__(
        self,
        extractor: Optional[DataExtractor] = None,
        transformer: Optional[DataTransformer] = None,
        loader: Optional[DataLoader] = None,
        enable_quality_checks: bool = True
    ):
        """
        Initialize ETL pipeline
        
        Args:
            extractor: Data extractor instance
            transformer: Data transformer instance
            loader: Data loader instance
            enable_quality_checks: Enable data quality validation
        """
        self.extractor = extractor or DataExtractor(source_type=DataSourceType.CSV)
        self.transformer = transformer or DataTransformer(enable_quality_checks=enable_quality_checks)
        self.loader = loader or DataLoader(destination=LoadDestination.DATABASE)
        self.enable_quality_checks = enable_quality_checks
        
        logger.info("ETL Pipeline initialized", extra={
            "extra_fields": {
                "quality_checks": enable_quality_checks
            }
        })
    
    def run(
        self,
        source: str,
        destination: str,
        extract_kwargs: Optional[Dict[str, Any]] = None,
        transform_kwargs: Optional[Dict[str, Any]] = None,
        load_kwargs: Optional[Dict[str, Any]] = None
    ) -> ETLPipelineResult:
        """
        Run the complete ETL pipeline
        
        Args:
            source: Source path or identifier
            destination: Destination path or identifier
            extract_kwargs: Additional extraction parameters
            transform_kwargs: Additional transformation parameters
            load_kwargs: Additional load parameters
            
        Returns:
            ETL pipeline execution result
        """
        start_time = time.time()
        errors = []
        records_extracted = 0
        records_transformed = 0
        records_loaded = 0
        records_valid = 0
        records_invalid = 0
        quality_score = 0.0
        quality_report = None
        
        logger.info("Starting ETL pipeline", extra={
            "extra_fields": {
                "source": source,
                "destination": destination,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        try:
            # EXTRACT
            try:
                extract_kwargs = extract_kwargs or {}
                df_extracted = self.extractor.extract(source, **extract_kwargs)
                records_extracted = len(df_extracted)
                logger.info(f"Extraction complete: {records_extracted} records")
            except Exception as e:
                error_msg = f"Extraction failed: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                raise
            
            # TRANSFORM
            try:
                transform_kwargs = transform_kwargs or {}
                df_transformed, quality_report_obj = self.transformer.transform(
                    df_extracted,
                    validate=self.enable_quality_checks
                )
                records_transformed = len(df_transformed)
                records_valid = quality_report_obj.valid_rows
                records_invalid = quality_report_obj.invalid_rows
                quality_score = quality_report_obj.quality_score
                quality_report = quality_report_obj.to_dict()
                logger.info(f"Transformation complete: {records_transformed} records (Quality: {quality_score:.2%})")
            except Exception as e:
                error_msg = f"Transformation failed: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                raise
            
            # LOAD
            try:
                load_kwargs = load_kwargs or {}
                load_result = self.loader.load(df_transformed, destination, mode='replace', **load_kwargs)
                records_loaded = load_result.get('total_processed', len(df_transformed))
                logger.info(f"Load complete: {records_loaded} records")
            except Exception as e:
                error_msg = f"Load failed: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                raise
            
            duration = time.time() - start_time
            
            result = ETLPipelineResult(
                success=True,
                records_extracted=records_extracted,
                records_transformed=records_transformed,
                records_loaded=records_loaded,
                records_valid=records_valid,
                records_invalid=records_invalid,
                quality_score=quality_score,
                duration_seconds=duration,
                errors=errors,
                quality_report=quality_report
            )
            
            logger.info("ETL pipeline completed successfully", extra={
                "extra_fields": result.to_dict()
            })
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"ETL pipeline failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True, extra={
                "extra_fields": {
                    "duration_seconds": duration,
                    "errors": errors
                }
            })
            
            return ETLPipelineResult(
                success=False,
                records_extracted=records_extracted,
                records_transformed=records_transformed,
                records_loaded=records_loaded,
                records_valid=records_valid,
                records_invalid=records_invalid,
                quality_score=quality_score,
                duration_seconds=duration,
                errors=errors,
                quality_report=quality_report
            )


def run_etl_legacy(data_file: str = 'data/sample_sales.csv', db_file: str = 'sales.db') -> Dict[str, Any]:
    """
    Legacy ETL function for backward compatibility
    
    Args:
        data_file: Path to source CSV file
        db_file: Path to destination database
        
    Returns:
        ETL result dictionary
    """
    try:
        # Use legacy modules if modern ones are not available
        import extract
        import transform
        from backend.load import save_to_db
        
        # Extract
        df = extract.extract(data_file)
        records_extracted = len(df)
        
        # Transform
        df = transform.transform(df)
        records_transformed = len(df)
        
        # Load
        save_to_db(df, mode='replace')
        records_loaded = records_transformed
        
        return {
            "success": True,
            "records_extracted": records_extracted,
            "records_transformed": records_transformed,
            "records_loaded": records_loaded,
            "message": "ETL pipeline completed successfully"
        }
    except Exception as e:
        logger.error(f"Legacy ETL failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
