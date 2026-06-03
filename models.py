from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class Tenant(db.Model):
    """Business tenant — each seller is a tenant"""
    __tablename__ = 'tenants'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    whatsapp_phone = db.Column(db.String(20))
    subscription_tier = db.Column(db.String(50), default='free')  # free, starter, pro
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    users = db.relationship('User', back_populates='tenant', cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', back_populates='tenant', cascade='all, delete-orphan')
    orders = db.relationship('Order', back_populates='tenant', cascade='all, delete-orphan')
    customers = db.relationship('Customer', back_populates='tenant', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Tenant {self.name}>'

class User(db.Model):
    """Users within a tenant"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='seller')  # seller, admin, support
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    tenant = db.relationship('Tenant', back_populates='users')
    
    __table_args__ = (db.UniqueConstraint('tenant_id', 'email', name='uq_tenant_user_email'),)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Customer(db.Model):
    """Customer profile — aggregates conversations and orders"""
    __tablename__ = 'customers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    phone = db.Column(db.String(20))
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    total_spent = db.Column(db.Float, default=0.0)
    order_count = db.Column(db.Integer, default=0)
    last_order_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    tenant = db.relationship('Tenant', back_populates='customers')
    conversations = db.relationship('Conversation', back_populates='customer')
    orders = db.relationship('Order', back_populates='customer')
    
    __table_args__ = (db.Index('ix_tenant_phone', 'tenant_id', 'phone'),)
    
    def __repr__(self):
        return f'<Customer {self.name}>'

class Conversation(db.Model):
    """Messages from WhatsApp/Instagram — groups by customer"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey('customers.id'), nullable=True)
    external_id = db.Column(db.String(255))  # WhatsApp message ID or Instagram thread ID
    channel = db.Column(db.String(50), default='whatsapp')  # whatsapp, instagram, facebook
    customer_phone = db.Column(db.String(20))
    customer_name = db.Column(db.String(255))
    message_text = db.Column(db.Text)
    message_direction = db.Column(db.String(20), default='inbound')  # inbound, outbound
    status = db.Column(db.String(50), default='open')  # open, replied, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tenant = db.relationship('Tenant', back_populates='conversations')
    customer = db.relationship('Customer', back_populates='conversations')
    orders = db.relationship('Order', back_populates='conversation')
    
    __table_args__ = (
        db.Index('ix_conversation_tenant_channel', 'tenant_id', 'channel'),
        db.Index('ix_conversation_tenant_status', 'tenant_id', 'status'),
    )
    
    def __repr__(self):
        return f'<Conversation {self.id}>'

class Order(db.Model):
    """Orders created from conversations"""
    __tablename__ = 'orders'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=True)
    customer_id = db.Column(db.String(36), db.ForeignKey('customers.id'), nullable=True)
    order_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(50), default='enquiry')  # enquiry, confirmed, paid, dispatched, delivered
    items = db.Column(db.JSON)  # [{product: "...", qty: 2, price: 500}, ...]
    total_amount = db.Column(db.Float)
    payment_status = db.Column(db.String(50), default='pending')  # pending, completed, failed
    payment_link = db.Column(db.String(500))
    payment_link_id = db.Column(db.String(255))  # Stripe/Razorpay ID
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tenant = db.relationship('Tenant', back_populates='orders')
    conversation = db.relationship('Conversation', back_populates='orders')
    customer = db.relationship('Customer', back_populates='orders')
    
    __table_args__ = (db.Index('ix_order_tenant_status', 'tenant_id', 'status'),)
    
    def __repr__(self):
        return f'<Order {self.order_number}>'

class Payment(db.Model):
    """Payment records for orders"""
    __tablename__ = 'payments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=False)
    order_id = db.Column(db.String(36), db.ForeignKey('orders.id'), nullable=True)
    external_id = db.Column(db.String(255))  # Stripe/Razorpay payment ID
    amount = db.Column(db.Float)
    status = db.Column(db.String(50))  # pending, completed, failed
    payment_method = db.Column(db.String(50))  # upi, card, netbanking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.Index('ix_payment_tenant_status', 'tenant_id', 'status'),)