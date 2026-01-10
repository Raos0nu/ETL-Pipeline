"""
Modern data extraction module with support for multiple data sources
"""
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
import io
import csv

try:
    from backend.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    """Supported data source types"""
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    DATABASE = "database"
    API = "api"


class DataExtractor:
    """Modern data extractor with support for multiple sources"""
    
    def __init__(self, source_type: DataSourceType = DataSourceType.CSV, **kwargs):
        """
        Initialize extractor
        
        Args:
            source_type: Type of data source
            **kwargs: Source-specific configuration
        """
        self.source_type = source_type
        self.config = kwargs
        logger.info(f"Initialized extractor for {source_type.value}", extra={
            "extra_fields": {"source_type": source_type.value}
        })
    
    def extract(self, source: str, **kwargs) -> pd.DataFrame:
        """
        Extract data from source
        
        Args:
            source: Path or identifier for data source
            **kwargs: Additional extraction parameters
            
        Returns:
            Extracted data as DataFrame
        """
        try:
            logger.info(f"Extracting data from {source}", extra={
                "extra_fields": {"source": source, "source_type": self.source_type.value}
            })
            
            if self.source_type == DataSourceType.CSV:
                return self._extract_csv(source, **kwargs)
            elif self.source_type == DataSourceType.JSON:
                return self._extract_json(source, **kwargs)
            elif self.source_type == DataSourceType.EXCEL:
                return self._extract_excel(source, **kwargs)
            elif self.source_type == DataSourceType.DATABASE:
                return self._extract_database(source, **kwargs)
            elif self.source_type == DataSourceType.API:
                return self._extract_api(source, **kwargs)
            else:
                raise ValueError(f"Unsupported source type: {self.source_type}")
                
        except Exception as e:
            logger.error(f"Failed to extract data from {source}", exc_info=True, extra={
                "extra_fields": {"source": source, "error": str(e)}
            })
            raise
    
    def _extract_csv(self, file_path: str, **kwargs) -> pd.DataFrame:
        """Extract data from CSV file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"CSV file not found: {file_path}, creating empty DataFrame")
            return pd.DataFrame(columns=['order_id', 'product', 'quantity', 'price'])
        
        try:
            df = pd.read_csv(
                file_path,
                encoding=kwargs.get('encoding', 'utf-8'),
                on_bad_lines=kwargs.get('on_bad_lines', 'skip'),
                dtype=kwargs.get('dtype', None),
                parse_dates=kwargs.get('parse_dates', False)
            )
            
            logger.info(f"Extracted {len(df)} rows from CSV", extra={
                "extra_fields": {"rows": len(df), "columns": list(df.columns)}
            })
            return df
            
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}", exc_info=True)
            raise
    
    def _extract_json(self, file_path: str, **kwargs) -> pd.DataFrame:
        """Extract data from JSON file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"JSON file not found: {file_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_json(
                file_path,
                orient=kwargs.get('orient', 'records'),
                lines=kwargs.get('lines', False)
            )
            logger.info(f"Extracted {len(df)} rows from JSON")
            return df
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}", exc_info=True)
            raise
    
    def _extract_excel(self, file_path: str, **kwargs) -> pd.DataFrame:
        """Extract data from Excel file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"Excel file not found: {file_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_excel(
                file_path,
                sheet_name=kwargs.get('sheet_name', 0),
                engine=kwargs.get('engine', 'openpyxl')
            )
            logger.info(f"Extracted {len(df)} rows from Excel")
            return df
        except Exception as e:
            logger.error(f"Error reading Excel file {file_path}", exc_info=True)
            raise
    
    def _extract_database(self, query: str, **kwargs) -> pd.DataFrame:
        """Extract data from database"""
        # This would be implemented with SQLAlchemy
        # For now, return empty DataFrame
        logger.warning("Database extraction not fully implemented")
        return pd.DataFrame()
    
    def _extract_api(self, url: str, **kwargs) -> pd.DataFrame:
        """Extract data from API endpoint"""
        # This would use requests library
        # For now, return empty DataFrame
        logger.warning("API extraction not fully implemented")
        return pd.DataFrame()
    
    def extract_from_string(self, content: str, format: str = 'csv') -> pd.DataFrame:
        """
        Extract data from string content
        
        Args:
            content: String content to parse
            format: Format of the content (csv, json)
            
        Returns:
            Extracted data as DataFrame
        """
        try:
            if format.lower() == 'csv':
                stream = io.StringIO(content)
                df = pd.read_csv(stream)
                logger.info(f"Extracted {len(df)} rows from string content")
                return df
            elif format.lower() == 'json':
                df = pd.read_json(io.StringIO(content))
                logger.info(f"Extracted {len(df)} rows from JSON string")
                return df
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error("Error extracting from string content", exc_info=True)
            raise


# Legacy function for backward compatibility
def extract(file_path: str) -> pd.DataFrame:
    """
    Legacy extraction function for backward compatibility
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Extracted data as DataFrame
    """
    extractor = DataExtractor(source_type=DataSourceType.CSV)
    return extractor.extract(file_path)
