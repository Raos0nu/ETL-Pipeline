"""
Modern data transformation module with data quality checks
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from backend.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class DataQualityReport:
    """Data quality metrics"""
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicates: int
    missing_values: Dict[str, int]
    data_types_correct: bool
    quality_score: float
    issues: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "duplicates": self.duplicates,
            "missing_values": self.missing_values,
            "data_types_correct": self.data_types_correct,
            "quality_score": round(self.quality_score, 2),
            "issues": self.issues
        }


class DataTransformer:
    """Modern data transformer with quality checks"""
    
    # Expected schema
    REQUIRED_COLUMNS = ['order_id', 'product', 'quantity', 'price']
    EXPECTED_DTYPES = {
        'order_id': 'int64',
        'product': 'object',
        'quantity': 'int64',
        'price': 'float64'
    }
    
    def __init__(self, enable_quality_checks: bool = True, drop_invalid: bool = True):
        """
        Initialize transformer
        
        Args:
            enable_quality_checks: Enable data quality validation
            drop_invalid: Drop invalid rows instead of raising errors
        """
        self.enable_quality_checks = enable_quality_checks
        self.drop_invalid = drop_invalid
        logger.info("Initialized data transformer", extra={
            "extra_fields": {
                "quality_checks": enable_quality_checks,
                "drop_invalid": drop_invalid
            }
        })
    
    def transform(self, df: pd.DataFrame, validate: Optional[bool] = None) -> Tuple[pd.DataFrame, DataQualityReport]:
        """
        Transform data with quality checks
        
        Args:
            df: Input DataFrame
            validate: Override enable_quality_checks if provided
            
        Returns:
            Tuple of (transformed DataFrame, quality report)
        """
        validate = validate if validate is not None else self.enable_quality_checks
        
        logger.info(f"Transforming data: {len(df)} rows", extra={
            "extra_fields": {"rows": len(df), "validate": validate}
        })
        
        original_count = len(df)
        df = df.copy()
        
        # Data quality checks
        if validate:
            df, quality_report = self._check_quality(df)
        else:
            quality_report = DataQualityReport(
                total_rows=len(df),
                valid_rows=len(df),
                invalid_rows=0,
                duplicates=0,
                missing_values={},
                data_types_correct=True,
                quality_score=1.0,
                issues=[]
            )
        
        # Apply transformations
        df = self._apply_transformations(df)
        
        logger.info(f"Transformation complete: {len(df)} rows output", extra={
            "extra_fields": {
                "input_rows": original_count,
                "output_rows": len(df),
                "quality_score": quality_report.quality_score
            }
        })
        
        return df, quality_report
    
    def _check_quality(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, DataQualityReport]:
        """Perform data quality checks"""
        issues = []
        original_count = len(df)
        
        # Check required columns
        missing_columns = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            issues.append(f"Missing columns: {missing_columns}")
            logger.warning(f"Missing required columns: {missing_columns}")
        
        # Check for duplicates
        duplicates = df.duplicated(subset=['order_id'], keep='first').sum() if 'order_id' in df.columns else 0
        
        # Check missing values
        missing_values = {}
        for col in self.REQUIRED_COLUMNS:
            if col in df.columns:
                missing_count = df[col].isna().sum()
                if missing_count > 0:
                    missing_values[col] = int(missing_count)
                    issues.append(f"Missing values in {col}: {missing_count}")
        
        # Validate data types and values
        valid_mask = pd.Series([True] * len(df), index=df.index)
        
        if 'order_id' in df.columns:
            # Order ID must be positive integer
            valid_mask &= (df['order_id'].notna()) & (df['order_id'] > 0)
            issues_count = (~valid_mask).sum()
            if issues_count > 0:
                issues.append(f"Invalid order_id: {issues_count} rows")
        
        if 'product' in df.columns:
            # Product must be non-empty string
            valid_mask &= (df['product'].notna()) & (df['product'].astype(str).str.strip() != '')
            issues_count = (~valid_mask).sum()
            if issues_count > 0:
                issues.append(f"Invalid product: {issues_count} rows")
        
        if 'quantity' in df.columns:
            # Quantity must be positive integer
            valid_mask &= (df['quantity'].notna()) & (df['quantity'] > 0)
            issues_count = (~valid_mask).sum()
            if issues_count > 0:
                issues.append(f"Invalid quantity: {issues_count} rows")
        
        if 'price' in df.columns:
            # Price must be positive number
            valid_mask &= (df['price'].notna()) & (df['price'] > 0)
            issues_count = (~valid_mask).sum()
            if issues_count > 0:
                issues.append(f"Invalid price: {issues_count} rows")
        
        # Filter invalid rows
        invalid_count = (~valid_mask).sum()
        if invalid_count > 0:
            if self.drop_invalid:
                df = df[valid_mask].copy()
                logger.warning(f"Dropped {invalid_count} invalid rows", extra={
                    "extra_fields": {"dropped_rows": invalid_count}
                })
            else:
                issues.append(f"{invalid_count} rows have invalid data")
        
        # Calculate quality score
        valid_rows = len(df)
        quality_score = valid_rows / original_count if original_count > 0 else 0.0
        
        # Check data types (simplified check)
        data_types_correct = True
        if 'order_id' in df.columns and not pd.api.types.is_integer_dtype(df['order_id']):
            data_types_correct = False
            issues.append("order_id is not integer type")
        
        quality_report = DataQualityReport(
            total_rows=original_count,
            valid_rows=valid_rows,
            invalid_rows=invalid_count,
            duplicates=int(duplicates),
            missing_values=missing_values,
            data_types_correct=data_types_correct,
            quality_score=quality_score,
            issues=issues
        )
        
        if issues:
            logger.warning("Data quality issues detected", extra={
                "extra_fields": {"issues": issues, "quality_score": quality_score}
            })
        
        return df, quality_report
    
    def _apply_transformations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply business logic transformations"""
        # Calculate total_price
        if 'quantity' in df.columns and 'price' in df.columns:
            df['total_price'] = df['quantity'] * df['price']
            df['total_price'] = df['total_price'].round(2)
        else:
            logger.warning("Cannot calculate total_price: missing quantity or price columns")
            df['total_price'] = 0.0
        
        # Add timestamp if not present
        if 'created_at' not in df.columns:
            df['created_at'] = datetime.utcnow()
        
        # Ensure data types
        if 'order_id' in df.columns:
            df['order_id'] = pd.to_numeric(df['order_id'], errors='coerce').astype('Int64')
        if 'quantity' in df.columns:
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').astype('Int64')
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').astype('float64')
        
        return df


# Legacy function for backward compatibility
def transform(data: pd.DataFrame) -> pd.DataFrame:
    """
    Legacy transformation function for backward compatibility
    
    Args:
        data: Input DataFrame
        
    Returns:
        Transformed DataFrame
    """
    transformer = DataTransformer(enable_quality_checks=False)
    df, _ = transformer.transform(data, validate=False)
    return df
