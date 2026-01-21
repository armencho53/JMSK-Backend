"""Base repository with common CRUD operations"""
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from app.data.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common database operations"""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def get_by_id(self, id: int, tenant_id: Optional[int] = None) -> Optional[ModelType]:
        """Get a single record by ID"""
        query = self.db.query(self.model).filter(self.model.id == id)
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.filter(self.model.tenant_id == tenant_id)
        return query.first()
    
    def get_all(
        self,
        tenant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get all records with pagination"""
        query = self.db.query(self.model)
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.filter(self.model.tenant_id == tenant_id)
        return query.offset(skip).limit(limit).all()
    
    def create(self, obj: ModelType) -> ModelType:
        """Create a new record"""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def update(self, obj: ModelType) -> ModelType:
        """Update an existing record"""
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def delete(self, obj: ModelType) -> None:
        """Delete a record"""
        self.db.delete(obj)
        self.db.commit()
    
    def count(self, tenant_id: Optional[int] = None) -> int:
        """Count records"""
        query = self.db.query(self.model)
        if tenant_id is not None and hasattr(self.model, 'tenant_id'):
            query = query.filter(self.model.tenant_id == tenant_id)
        return query.count()
