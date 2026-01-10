"""
Modern data loading module with support for multiple destinations
"""
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import csv
import io

try:
    from backend.models import db_manager, SalesRecord
    from backend.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    db_manager = None


class LoadDestination(str, Enum):
    """Supported load destinations"""
    DATABASE = "database"
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"


class DataLoader:
    """Modern data loader with support for multiple destinations"""
    
    def __init__(self, destination: LoadDestination = LoadDestination.DATABASE, **kwargs):
        """
        Initialize loader
        
        Args:
            destination: Type of destination
            **kwargs: Destination-specific configuration
        """
        self.destination = destination
        self.config = kwargs
        logger.info(f"Initialized loader for {destination.value}", extra={
            "extra_fields": {"destination": destination.value}
        })
    
    def load(self, df: pd.DataFrame, target: str, mode: str = 'replace', **kwargs) -> Dict[str, Any]:
        """
        Load data to destination
        
        Args:
            df: DataFrame to load
            target: Target path or identifier
            mode: Load mode ('replace', 'append', 'upsert')
            **kwargs: Additional load parameters
            
        Returns:
            Load result metadata
        """
        try:
            logger.info(f"Loading {len(df)} rows to {target}", extra={
                "extra_fields": {
                    "rows": len(df),
                    "destination": self.destination.value,
                    "target": target,
                    "mode": mode
                }
            })
            
            if self.destination == LoadDestination.DATABASE:
                return self._load_database(df, target, mode, **kwargs)
            elif self.destination == LoadDestination.CSV:
                return self._load_csv(df, target, mode, **kwargs)
            elif self.destination == LoadDestination.JSON:
                return self._load_json(df, target, mode, **kwargs)
            elif self.destination == LoadDestination.EXCEL:
                return self._load_excel(df, target, mode, **kwargs)
            else:
                raise ValueError(f"Unsupported destination: {self.destination}")
                
        except Exception as e:
            logger.error(f"Failed to load data to {target}", exc_info=True, extra={
                "extra_fields": {"target": target, "error": str(e)}
            })
            raise
    
    def _load_database(self, df: pd.DataFrame, table_name: str, mode: str, **kwargs) -> Dict[str, Any]:
        """Load data to database"""
        if not db_manager:
            raise RuntimeError("Database manager not available")
        
        try:
            records_loaded = 0
            records_updated = 0
            
            with db_manager.get_session() as session:
                if mode == 'replace':
                    # Delete all existing records
                    session.query(SalesRecord).delete()
                    logger.info("Cleared existing records from database")
                
                # Insert or update records
                for _, row in df.iterrows():
                    existing = None
                    if 'order_id' in row:
                        existing = session.query(SalesRecord).filter_by(order_id=int(row['order_id'])).first()
                    
                    if existing:
                        if mode == 'upsert':
                            # Update existing record
                            existing.product = str(row.get('product', existing.product))
                            existing.quantity = int(row.get('quantity', existing.quantity))
                            existing.price = float(row.get('price', existing.price))
                            existing.total_price = float(row.get('total_price', existing.total_price))
                            records_updated += 1
                        elif mode == 'replace':
                            # Delete and create new
                            session.delete(existing)
                            existing = None
                    
                    if not existing:
                        # Create new record
                        record = SalesRecord(
                            order_id=int(row.get('order_id', 0)),
                            product=str(row.get('product', '')),
                            quantity=int(row.get('quantity', 0)),
                            price=float(row.get('price', 0.0)),
                            total_price=float(row.get('total_price', 0.0))
                        )
                        session.add(record)
                        records_loaded += 1
                
                session.commit()
            
            result = {
                "records_loaded": records_loaded,
                "records_updated": records_updated,
                "total_processed": records_loaded + records_updated,
                "mode": mode
            }
            
            logger.info(f"Database load complete", extra={
                "extra_fields": result
            })
            
            return result
            
        except Exception as e:
            logger.error("Database load failed", exc_info=True)
            raise
    
    def _load_csv(self, df: pd.DataFrame, file_path: str, mode: str, **kwargs) -> Dict[str, Any]:
        """Load data to CSV file"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if mode == 'append' and file_path.exists():
                # Append to existing file
                existing_df = pd.read_csv(file_path)
                df = pd.concat([existing_df, df], ignore_index=True)
            
            # Remove duplicates if requested
            if kwargs.get('remove_duplicates', True) and 'order_id' in df.columns:
                df = df.drop_duplicates(subset=['order_id'], keep='last')
            
            # Save to CSV
            df.to_csv(file_path, index=False, encoding='utf-8')
            
            result = {
                "records_loaded": len(df),
                "file_path": str(file_path),
                "mode": mode
            }
            
            logger.info(f"CSV load complete: {len(df)} rows", extra={
                "extra_fields": result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"CSV load failed: {file_path}", exc_info=True)
            raise
    
    def _load_json(self, df: pd.DataFrame, file_path: str, mode: str, **kwargs) -> Dict[str, Any]:
        """Load data to JSON file"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if mode == 'append' and file_path.exists():
                existing_df = pd.read_json(file_path, orient='records')
                df = pd.concat([existing_df, df], ignore_index=True)
            
            df.to_json(file_path, orient='records', indent=2)
            
            result = {
                "records_loaded": len(df),
                "file_path": str(file_path),
                "mode": mode
            }
            
            logger.info(f"JSON load complete: {len(df)} rows")
            return result
            
        except Exception as e:
            logger.error(f"JSON load failed: {file_path}", exc_info=True)
            raise
    
    def _load_excel(self, df: pd.DataFrame, file_path: str, mode: str, **kwargs) -> Dict[str, Any]:
        """Load data to Excel file"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            sheet_name = kwargs.get('sheet_name', 'Sheet1')
            engine = kwargs.get('engine', 'openpyxl')
            
            if mode == 'append' and file_path.exists():
                existing_df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)
                df = pd.concat([existing_df, df], ignore_index=True)
            
            df.to_excel(file_path, sheet_name=sheet_name, index=False, engine=engine)
            
            result = {
                "records_loaded": len(df),
                "file_path": str(file_path),
                "mode": mode
            }
            
            logger.info(f"Excel load complete: {len(df)} rows")
            return result
            
        except Exception as e:
            logger.error(f"Excel load failed: {file_path}", exc_info=True)
            raise


def save_to_db(df: pd.DataFrame, mode: str = 'replace') -> Dict[str, Any]:
    """
    Legacy function for backward compatibility
    
    Args:
        df: DataFrame to save
        mode: Load mode ('replace', 'append', 'upsert')
        
    Returns:
        Load result metadata
    """
    loader = DataLoader(destination=LoadDestination.DATABASE)
    return loader.load(df, target='sales', mode=mode)
