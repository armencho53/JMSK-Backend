"""Order business logic service"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.order_line_item_repository import OrderLineItemRepository
from app.data.repositories.contact_repository import ContactRepository
from app.data.models.order import Order
from app.data.models.order_line_item import OrderLineItem
from app.schemas.order import OrderResponse, OrderLineItemResponse
from app.domain.services.supply_tracking_service import SupplyTrackingService
from app.domain.exceptions import ResourceNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class OrderService:
    """
    Service for order business logic with clean architecture.
    
    Implements business logic for order CRUD operations with support for
    multiple line items per order and optional metal deposits during order
    creation. All operations enforce multi-tenant isolation and maintain
    data integrity through atomic transactions.
    
    Requirements: 3.6, 3.9, 5.8
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.line_item_repo = OrderLineItemRepository(db)
        self.contact_repo = ContactRepository(db)
        self.supply_tracking_service = SupplyTrackingService(db)
    
    def create_order_with_deposit(
        self,
        order_data: dict,
        tenant_id: int,
        user_id: int
    ) -> OrderResponse:
        """
        Create order with line items and optional metal deposit in atomic transaction.
        
        This method handles the complete order creation workflow:
        1. Validates contact exists and resolves company_id
        2. Creates the order record
        3. Creates all line items associated with the order
        4. Optionally records a metal deposit for the company
        5. All operations wrapped in a transaction (atomic)
        
        Args:
            order_data: Dictionary containing:
                - contact_id: ID of the contact placing the order (required)
                - due_date: Expected completion date (optional)
                - status: Order status (optional, defaults to PENDING)
                - line_items: List of line item dictionaries (required, min 1)
                - metal_deposit: Optional deposit dictionary with:
                    - metal_id: ID of the metal
                    - quantity_grams: Quantity in grams
                    - notes: Optional notes
            tenant_id: Tenant ID for multi-tenant isolation
            user_id: ID of the user creating the order
        
        Returns:
            OrderResponse with all line items populated
        
        Raises:
            ResourceNotFoundError: If contact is not found
            ValidationError: If line_items is empty or invalid
            SQLAlchemyError: If database transaction fails (triggers rollback)
        
        Requirements: 3.6, 3.9, 5.8
        """
        try:
            # Validate contact exists and get company_id
            contact = self.contact_repo.get_by_id(order_data['contact_id'], tenant_id)
            if not contact:
                raise ResourceNotFoundError("Contact", order_data['contact_id'])
            
            company_id = contact.company_id
            
            # Validate line items
            line_items_data = order_data.get('line_items', [])
            if not line_items_data or len(line_items_data) == 0:
                raise ValidationError("Order must have at least one line item")
            
            # Generate order number (simple implementation - can be enhanced)
            order_number = self._generate_order_number(tenant_id)
            
            # Create order
            order = Order(
                tenant_id=tenant_id,
                order_number=order_number,
                contact_id=order_data['contact_id'],
                company_id=company_id,
                status=order_data.get('status', 'PENDING'),
                due_date=order_data.get('due_date')
            )
            order = self.order_repo.create(order)
            
            # Create line items
            created_line_items = []
            for line_item_data in line_items_data:
                line_item = OrderLineItem(
                    tenant_id=tenant_id,
                    order_id=order.id,
                    product_description=line_item_data['product_description'],
                    specifications=line_item_data.get('specifications'),
                    metal_id=line_item_data.get('metal_id'),
                    quantity=line_item_data.get('quantity', 1),
                    target_weight_per_piece=line_item_data.get('target_weight_per_piece'),
                    initial_total_weight=line_item_data.get('initial_total_weight'),
                    price=line_item_data.get('price'),
                    labor_cost=line_item_data.get('labor_cost')
                )
                created_line_item = self.line_item_repo.create(line_item)
                created_line_items.append(created_line_item)
            
            # Process optional metal deposit
            if 'metal_deposit' in order_data and order_data['metal_deposit']:
                deposit_data = order_data['metal_deposit']
                self.supply_tracking_service.record_company_deposit(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    metal_id=deposit_data['metal_id'],
                    quantity_grams=deposit_data['quantity_grams'],
                    user_id=user_id,
                    notes=deposit_data.get('notes')
                )
            
            # Commit transaction
            self.db.commit()
            
            # Refresh order to get relationships
            self.db.refresh(order)
            
            # Return response with line items
            return self.get_order_with_line_items(order.id, tenant_id)
        
        except (ResourceNotFoundError, ValidationError):
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating order: {str(e)}")
            raise ValidationError(f"Failed to create order: {str(e)}")
    def get_all_orders(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[OrderResponse]:
        """
        Get all orders for a tenant with pagination.

        Returns orders with:
        - Contact and company information
        - All line items with metal names
        - Proper multi-tenant isolation

        Args:
            tenant_id: Tenant ID for isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of OrderResponse objects
        """
        try:
            # Get orders from repository
            orders = self.order_repo.get_all(tenant_id=tenant_id, skip=skip, limit=limit)

            # Convert to response format with line items
            order_responses = []
            for order in orders:
                # Get line items for this order
                line_items = self.line_item_repo.get_by_order_id(
                    order_id=order.id,
                    tenant_id=tenant_id
                )

                # Convert line items to response format
                line_item_responses = [
                    OrderLineItemResponse(
                        id=item.id,
                        order_id=item.order_id,
                        metal_id=item.metal_id,
                        metal_name=item.metal.name if item.metal else None,
                        quantity=item.quantity,
                        weight=item.weight,
                        description=item.description,
                        created_at=item.created_at,
                        updated_at=item.updated_at
                    )
                    for item in line_items
                ]

                # Build order response
                order_response = OrderResponse(
                    id=order.id,
                    order_number=order.order_number,
                    contact_id=order.contact_id,
                    contact_name=order.contact.name if order.contact else None,
                    company_id=order.company_id,
                    company_name=order.company.name if order.company else None,
                    due_date=order.due_date,
                    status=order.status,
                    line_items=line_item_responses,
                    created_at=order.created_at,
                    updated_at=order.updated_at
                )
                order_responses.append(order_response)

            return order_responses

        except SQLAlchemyError as e:
            logger.error(f"Database error getting orders: {str(e)}")
            raise ValidationError(f"Failed to retrieve orders: {str(e)}")

    
    def update_order(
        self,
        order_id: int,
        order_data: dict,
        tenant_id: int
    ) -> OrderResponse:
        """
        Update order and replace all line items.
        
        This method updates the order header fields and completely replaces
        all line items. The replacement strategy ensures data consistency:
        1. Deletes all existing line items
        2. Creates new line items from the provided data
        3. Updates order header fields
        
        Args:
            order_id: ID of the order to update
            order_data: Dictionary containing:
                - contact_id: New contact ID (optional)
                - due_date: New due date (optional)
                - status: New status (optional)
                - line_items: New list of line items (optional, if provided replaces all)
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            OrderResponse with updated line items
        
        Raises:
            ResourceNotFoundError: If order or contact is not found
            ValidationError: If line_items is empty when provided
        
        Requirements: 3.9
        """
        try:
            # Get existing order
            order = self.order_repo.get_by_id(order_id, tenant_id)
            if not order:
                raise ResourceNotFoundError("Order", order_id)
            
            # Update contact_id if provided and validate
            if 'contact_id' in order_data and order_data['contact_id']:
                contact = self.contact_repo.get_by_id(order_data['contact_id'], tenant_id)
                if not contact:
                    raise ResourceNotFoundError("Contact", order_data['contact_id'])
                order.contact_id = order_data['contact_id']
                order.company_id = contact.company_id
            
            # Update other order fields
            if 'due_date' in order_data:
                order.due_date = order_data['due_date']
            if 'status' in order_data:
                order.status = order_data['status']
            
            # Replace line items if provided
            if 'line_items' in order_data:
                line_items_data = order_data['line_items']
                
                if not line_items_data or len(line_items_data) == 0:
                    raise ValidationError("Order must have at least one line item")
                
                # Delete existing line items
                self.line_item_repo.delete_by_order(order_id, tenant_id)
                
                # Create new line items
                for line_item_data in line_items_data:
                    line_item = OrderLineItem(
                        tenant_id=tenant_id,
                        order_id=order_id,
                        product_description=line_item_data['product_description'],
                        specifications=line_item_data.get('specifications'),
                        metal_id=line_item_data.get('metal_id'),
                        quantity=line_item_data.get('quantity', 1),
                        target_weight_per_piece=line_item_data.get('target_weight_per_piece'),
                        initial_total_weight=line_item_data.get('initial_total_weight'),
                        price=line_item_data.get('price'),
                        labor_cost=line_item_data.get('labor_cost')
                    )
                    self.line_item_repo.create(line_item)
            
            # Update order
            order = self.order_repo.update(order)
            
            # Commit transaction
            self.db.commit()
            
            # Return response with line items
            return self.get_order_with_line_items(order_id, tenant_id)
        
        except (ResourceNotFoundError, ValidationError):
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating order: {str(e)}")
            raise ValidationError(f"Failed to update order: {str(e)}")
    
    def get_order_with_line_items(
        self,
        order_id: int,
        tenant_id: int
    ) -> OrderResponse:
        """
        Get order with all line items populated.
        
        Retrieves the order and all associated line items, including
        related entities (contact, company, metal) for complete order details.
        
        Args:
            order_id: ID of the order
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            OrderResponse with line_items array populated
        
        Raises:
            ResourceNotFoundError: If order is not found
        
        Requirements: 3.9, 3.10
        """
        order = self.order_repo.get_with_line_items(order_id, tenant_id)
        if not order:
            raise ResourceNotFoundError("Order", order_id)
        
        # Convert line items to response schema
        line_items_response = []
        for line_item in order.line_items:
            line_item_dict = {
                "id": line_item.id,
                "order_id": line_item.order_id,
                "product_description": line_item.product_description,
                "specifications": line_item.specifications,
                "metal_id": line_item.metal_id,
                "metal_name": line_item.metal.name if line_item.metal else None,
                "quantity": line_item.quantity,
                "target_weight_per_piece": line_item.target_weight_per_piece,
                "initial_total_weight": line_item.initial_total_weight,
                "price": line_item.price,
                "labor_cost": line_item.labor_cost,
                "created_at": line_item.created_at,
                "updated_at": line_item.updated_at
            }
            line_items_response.append(OrderLineItemResponse(**line_item_dict))
        
        # Build order response
        order_dict = {
            "id": order.id,
            "order_number": order.order_number,
            "tenant_id": order.tenant_id,
            "contact_id": order.contact_id,
            "company_id": order.company_id,
            "status": order.status,
            "due_date": order.due_date,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "line_items": line_items_response,
            # Deprecated single-line fields for backward compatibility
            "product_description": order.product_description,
            "specifications": order.specifications,
            "quantity": order.quantity,
            "price": order.price,
            "metal_id": order.metal_id,
            "metal_name": order.metal.name if order.metal else None,
            "target_weight_per_piece": order.target_weight_per_piece,
            "initial_total_weight": order.initial_total_weight,
            "labor_cost": order.labor_cost
        }
        
        # Add contact and company summaries if loaded
        if order.contact:
            from app.schemas.company import ContactSummary
            order_dict["contact"] = ContactSummary(
                id=order.contact.id,
                name=order.contact.name,
                email=order.contact.email,
                phone=order.contact.phone
            )
        
        if order.company:
            from app.schemas.contact import CompanySummary
            order_dict["company"] = CompanySummary(
                id=order.company.id,
                name=order.company.name,
                email=order.company.email,
                phone=order.company.phone
            )
        
        return OrderResponse(**order_dict)
    
    def _generate_order_number(self, tenant_id: int) -> str:
        """
        Generate unique order number for tenant.
        
        Simple implementation using count + 1. Can be enhanced with
        custom formatting, prefixes, or other business rules.
        
        Args:
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Unique order number string
        """
        count = self.order_repo.count(tenant_id)
        return f"ORD-{tenant_id}-{count + 1:06d}"
