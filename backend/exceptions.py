"""
Custom exceptions for the ETL Pipeline
"""
from typing import Optional, Dict, Any


class ETLPipelineError(Exception):
    """Base exception for ETL pipeline errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ExtractionError(ETLPipelineError):
    """Error during data extraction"""
    pass


class TransformationError(ETLPipelineError):
    """Error during data transformation"""
    pass


class LoadError(ETLPipelineError):
    """Error during data loading"""
    pass


class DataQualityError(ETLPipelineError):
    """Data quality validation error"""
    pass


class ValidationError(ETLPipelineError):
    """Data validation error"""
    pass


class DatabaseError(ETLPipelineError):
    """Database operation error"""
    pass
