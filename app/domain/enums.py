"""
Centralized system enum definitions.

These enums drive application branching logic (if/switch statements) and remain
as Python enums in code. They are NOT tenant-configurable.
"""
import enum


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"


class ShipmentStatus(str, enum.Enum):
    PREPARING = "PREPARING"
    SHIPPED = "SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"


class MetalType(str, enum.Enum):
    """Precious metal type categories for balance aggregation."""
    GOLD = "GOLD"
    SILVER = "SILVER"
    PLATINUM = "PLATINUM"
    PALLADIUM = "PALLADIUM"
    OTHER = "OTHER"
