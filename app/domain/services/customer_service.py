"""
DEPRECATED: Legacy customer business logic service.

This service is being replaced by ContactService as part of the
hierarchical contact system migration. Use app.domain.services.contact_service
for all new code.

Migration path: CustomerService -> ContactService
See: app/domain/services/contact_service.py
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.data.repositories.customer_repository import CustomerRepository
from app.data.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse, BalanceBreakdown
from app.domain.exceptions import ResourceNotFoundError, DuplicateResourceError, ValidationError


class CustomerService:
    """
    DEPRECATED: Service for customer business logic.
    Use ContactService instead.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = CustomerRepository(db)
    
    def get_all_customers(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[CustomerResponse]:
        """Get all customers for a tenant with optional search"""
        if search:
            customers = self.repository.search(tenant_id, search, skip, limit)
        else:
            customers = self.repository.get_all(tenant_id, skip, limit)
        
        # Enrich with balance
        result = []
        for customer in customers:
            balance = self.repository.get_balance(customer.id)
            customer_dict = self._to_response_dict(customer, balance)
            result.append(CustomerResponse(**customer_dict))
        
        return result
    
    def get_customer_by_id(self, customer_id: int, tenant_id: int) -> CustomerResponse:
        """Get a single customer by ID"""
        customer = self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            raise ResourceNotFoundError("Customer", customer_id)
        
        balance = self.repository.get_balance(customer.id)
        customer_dict = self._to_response_dict(customer, balance)
        return CustomerResponse(**customer_dict)
    
    def create_customer(self, customer_data: CustomerCreate, tenant_id: int) -> CustomerResponse:
        """Create a new customer"""
        # Check for duplicate email
        existing = self.repository.get_by_email(customer_data.email, tenant_id)
        if existing:
            raise DuplicateResourceError("Customer", "email", customer_data.email)
        
        # Create customer
        customer = Customer(
            **customer_data.dict(),
            tenant_id=tenant_id
        )
        customer = self.repository.create(customer)
        
        customer_dict = self._to_response_dict(customer, 0.0)
        return CustomerResponse(**customer_dict)
    
    def update_customer(
        self,
        customer_id: int,
        customer_data: CustomerUpdate,
        tenant_id: int
    ) -> CustomerResponse:
        """Update an existing customer"""
        customer = self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            raise ResourceNotFoundError("Customer", customer_id)
        
        # Check for duplicate email if changing
        if customer_data.email and customer_data.email != customer.email:
            existing = self.repository.get_by_email(customer_data.email, tenant_id)
            if existing:
                raise DuplicateResourceError("Customer", "email", customer_data.email)
        
        # Update fields
        for key, value in customer_data.dict(exclude_unset=True).items():
            setattr(customer, key, value)
        
        customer = self.repository.update(customer)
        balance = self.repository.get_balance(customer.id)
        customer_dict = self._to_response_dict(customer, balance)
        return CustomerResponse(**customer_dict)
    
    def delete_customer(self, customer_id: int, tenant_id: int) -> None:
        """Delete a customer"""
        customer = self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            raise ResourceNotFoundError("Customer", customer_id)
        
        # Business rule: Cannot delete customer with orders
        if self.repository.has_orders(customer_id):
            raise ValidationError("Cannot delete customer with existing orders")
        
        self.repository.delete(customer)
    
    def get_customer_balance(self, customer_id: int, tenant_id: int) -> BalanceBreakdown:
        """Get detailed balance breakdown for a customer"""
        customer = self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            raise ResourceNotFoundError("Customer", customer_id)
        
        # Import here to avoid circular dependency
        from app.data.models.order import Order, OrderStatus
        from sqlalchemy import func
        
        # Calculate balances by status
        total = self.db.query(func.sum(Order.price)).filter(
            Order.customer_id == customer_id
        ).scalar() or 0.0
        
        pending = self.db.query(func.sum(Order.price)).filter(
            Order.customer_id == customer_id,
            Order.status.in_([OrderStatus.PENDING, OrderStatus.IN_PROGRESS])
        ).scalar() or 0.0
        
        completed = self.db.query(func.sum(Order.price)).filter(
            Order.customer_id == customer_id,
            Order.status.in_([OrderStatus.COMPLETED, OrderStatus.SHIPPED])
        ).scalar() or 0.0
        
        return BalanceBreakdown(
            total=total,
            pending=pending,
            completed=completed
        )
    
    def _to_response_dict(self, customer: Customer, balance: float) -> dict:
        """Convert customer model to response dictionary"""
        return {
            "id": customer.id,
            "tenant_id": customer.tenant_id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "company_id": customer.company_id,
            "created_at": customer.created_at,
            "updated_at": customer.updated_at,
            "balance": balance
        }
