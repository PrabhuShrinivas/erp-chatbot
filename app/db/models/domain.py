import uuid
from datetime import date, datetime
from sqlalchemy import Column, String, Boolean, Date, Numeric, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class Party(Base):
    __tablename__ = 'parties'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    name = Column(Text, nullable=False)
    party_type = Column(Text, CheckConstraint("party_type IN ('customer', 'supplier', 'both')"), nullable=False)
    gstin = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class SalesOrder(Base):
    __tablename__ = 'sales_orders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    order_number = Column(Text, nullable=False, unique=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('parties.id'), nullable=False)
    order_date = Column(Date, nullable=False)
    promised_delivery_date = Column(Date, nullable=True)
    revised_delivery_date = Column(Date, nullable=True)
    actual_delivery_date = Column(Date, nullable=True)
    status = Column(Text, CheckConstraint("status IN ('open', 'partially_fulfilled', 'fulfilled', 'cancelled')"), nullable=False)
    total_amount = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    customer = relationship("Party", foreign_keys=[customer_id])
    items = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")

class SalesOrderItem(Base):
    __tablename__ = 'sales_order_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey('sales_orders.id', ondelete="CASCADE"), nullable=False)
    material_code = Column(Text, nullable=False)
    material_name = Column(Text, nullable=False)
    quantity = Column(Numeric(18, 3), nullable=False)
    unit = Column(Text, nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    line_amount = Column(Numeric(18, 2), nullable=False)
    quantity_delivered = Column(Numeric(18, 3), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    sales_order = relationship("SalesOrder", back_populates="items")

class PurchaseOrder(Base):
    __tablename__ = 'purchase_orders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    order_number = Column(Text, nullable=False, unique=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('parties.id'), nullable=False)
    order_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date, nullable=True)
    actual_delivery_date = Column(Date, nullable=True)
    status = Column(Text, CheckConstraint("status IN ('open', 'partially_received', 'received', 'cancelled')"), nullable=False)
    total_amount = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    supplier = relationship("Party", foreign_keys=[supplier_id])

class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    invoice_number = Column(Text, nullable=False, unique=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('parties.id'), nullable=False)
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey('sales_orders.id'), nullable=True)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    gross_amount = Column(Numeric(18, 2), nullable=False)
    status = Column(Text, CheckConstraint("status IN ('open', 'partially_paid', 'paid', 'cancelled')"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    customer = relationship("Party", foreign_keys=[customer_id])
    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])
    payments = relationship("Payment", back_populates="invoice")

class Payment(Base):
    __tablename__ = 'payments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    payment_number = Column(Text, nullable=False, unique=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('parties.id'), nullable=False)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoices.id'), nullable=True)
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey('sales_orders.id'), nullable=True)
    payment_method = Column(Text, nullable=True)
    reference_number = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    customer = relationship("Party", foreign_keys=[customer_id])
    invoice = relationship("Invoice", back_populates="payments")
    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])

class GoodsReceipt(Base):
    __tablename__ = 'goods_receipts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    receipt_number = Column(Text, nullable=False, unique=True)
    purchase_order_id = Column(UUID(as_uuid=True), ForeignKey('purchase_orders.id'), nullable=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('parties.id'), nullable=False)
    receipt_date = Column(Date, nullable=False)
    material_code = Column(Text, nullable=False)
    material_name = Column(Text, nullable=False)
    quantity_received = Column(Numeric(18, 3), nullable=False)
    unit = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    purchase_order = relationship("PurchaseOrder", foreign_keys=[purchase_order_id])
    supplier = relationship("Party", foreign_keys=[supplier_id])

class Inventory(Base):
    __tablename__ = 'inventory'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    material_code = Column(Text, nullable=False, unique=True)
    material_name = Column(Text, nullable=False)
    quantity_on_hand = Column(Numeric(18, 3), nullable=False)
    unit = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
