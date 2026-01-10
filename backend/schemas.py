"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class SalesRecordBase(BaseModel):
    """Base sales record schema"""
    order_id: int = Field(..., gt=0, description="Order ID must be greater than 0")
    product: str = Field(..., min_length=1, max_length=255, description="Product name")
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    
    @validator('product')
    def validate_product(cls, v):
        if not v or not v.strip():
            raise ValueError('Product name cannot be empty')
        return v.strip()
    
    @validator('price', 'quantity')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Value must be greater than 0')
        return v


class SalesRecordCreate(SalesRecordBase):
    """Schema for creating a sales record"""
    pass


class SalesRecordUpdate(BaseModel):
    """Schema for updating a sales record"""
    product: Optional[str] = Field(None, min_length=1, max_length=255)
    quantity: Optional[int] = Field(None, gt=0)
    price: Optional[float] = Field(None, gt=0)
    
    @validator('product')
    def validate_product(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Product name cannot be empty')
        return v
    
    @validator('price', 'quantity', pre=True)
    def validate_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Value must be greater than 0')
        return v


class SalesRecordResponse(BaseModel):
    """Schema for sales record response"""
    id: Optional[int] = None
    order_id: int
    product: str
    quantity: int
    price: float
    total_price: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(50, ge=1, le=1000, description="Records per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self) -> int:
        return self.per_page


class DateFilterParams(BaseModel):
    """Date filter parameters"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class BulkDeleteRequest(BaseModel):
    """Bulk delete request schema"""
    order_ids: List[int] = Field(..., min_items=1, description="List of order IDs to delete")


class ETLRunResponse(BaseModel):
    """ETL pipeline run response"""
    success: bool
    message: str
    records_processed: int
    records_valid: int
    records_invalid: int
    duration_seconds: float
    errors: Optional[List[str]] = None


class ProductAnalyticsResponse(BaseModel):
    """Product analytics response"""
    product: str
    total_quantity: int
    total_revenue: float
    order_count: int
    average_price: float


class TimeSeriesDataPoint(BaseModel):
    """Time series data point"""
    date: str
    revenue: float
    orders: int
    quantity: int


class StatsResponse(BaseModel):
    """Statistics response"""
    total_orders: int
    total_revenue: float
    average_order_value: float
    total_items_sold: int


class PaginatedResponse(BaseModel):
    """Paginated response"""
    success: bool
    data: List[SalesRecordResponse]
    stats: StatsResponse
    pagination: dict
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": [],
                "stats": {
                    "total_orders": 0,
                    "total_revenue": 0.0,
                    "average_order_value": 0.0,
                    "total_items_sold": 0
                },
                "pagination": {
                    "page": 1,
                    "per_page": 50,
                    "total_records": 0,
                    "total_pages": 1
                }
            }
        }
