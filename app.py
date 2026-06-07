import os
import logging
from flask import Flask, jsonify, request
from config import get_config
from models import db, Tenant, User, Conversation, Order, Customer
from auth import generate_token, token_required
from middleware import tenant_scoped, TenantFilter
import uuid
from flask_cors import CORS

logger = logging.getLogger(__name__)

"""
Flowmerce — Multi-tenant Social Commerce Backend
=====================================
Enables WhatsApp/Instagram-first businesses to manage orders, customers, and payments.

Architecture:
- Tenant isolation: every table has tenant_id
- JWT auth: login returns token with tenant_id embedded
- Webhook-ready: slot in WhatsApp/Instagram webhook receivers
- Event-driven: ready for async job processing

Endpoints are protected by @token_required decorator.
All queries are scoped to request.tenant_id via @tenant_scoped decorator.
"""

app = Flask(__name__)
CORS(app)

# Load config based on FLASK_ENV
config = get_config()
app.config.from_object(config)

# Initialize database
db.init_app(app)

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Tables may already exist: {e}")

# ============= HEALTH CHECK =============
@app.route('/health', methods=['GET'])
def health():
    """Test endpoint to verify server is running"""
    try:
        # Simple test by querying the database
        Tenant.query.first()
        return jsonify({
            'status': 'ok',
            'database': 'connected',
            'message': 'Flowmerce backend is running'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# ============= AUTH ENDPOINTS =============
@app.route('/auth/signup', methods=['POST'])
def signup():
    """Sign up a new tenant (business)"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password') or not data.get('business_name'):
            return jsonify({'error': 'Missing required fields: email, password, business_name'}), 400
        
        # Check if tenant already exists
        if Tenant.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Business email already registered'}), 400
        
        # Create tenant
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=data['business_name'],
            email=data['email']
        )
        db.session.add(tenant)
        db.session.flush()  # Get tenant ID before creating user
        
        # Create owner user
        user = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            email=data['email'],
            role='admin'
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        
        # Generate token
        token = generate_token(user.id, tenant.id)
        
        return jsonify({
            'message': 'Signup successful',
            'tenant_id': tenant.id,
            'user_id': user.id,
            'token': token
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    """Login existing user"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing email or password'}), 400
        
        # Find user by email (assumes email is unique per tenant in real scenario)
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate token
        token = generate_token(user.id, user.tenant_id)
        
        return jsonify({
            'message': 'Login successful',
            'tenant_id': user.tenant_id,
            'user_id': user.id,
            'token': token
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= CONVERSATION ENDPOINTS =============
@app.route('/conversations', methods=['GET'])
@token_required
@tenant_scoped
def list_conversations():
    """Get all conversations for the current tenant"""
    try:
        conversations = Conversation.query.filter_by(
            tenant_id=request.tenant_id
        ).order_by(Conversation.created_at.desc()).all()
        
        return jsonify({
            'conversations': [
                {
                    'id': c.id,
                    'customer_name': c.customer_name,
                    'customer_phone': c.customer_phone,
                    'channel': c.channel,
                    'message_text': c.message_text,
                    'status': c.status,
                    'created_at': c.created_at.isoformat()
                }
                for c in conversations
            ]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/conversations', methods=['POST'])
@token_required
@tenant_scoped
def create_conversation():
    """Create a conversation (usually from WhatsApp webhook)"""
    try:
        data = request.get_json()
        
        conversation = Conversation(
            id=str(uuid.uuid4()),
            tenant_id=request.tenant_id,
            external_id=data.get('external_id'),
            channel=data.get('channel', 'whatsapp'),
            customer_phone=data.get('customer_phone'),
            customer_name=data.get('customer_name'),
            message_text=data.get('message_text'),
            message_direction=data.get('direction', 'inbound')
        )
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify({
            'message': 'Conversation created',
            'conversation_id': conversation.id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============= CUSTOMER ENDPOINTS =============
@app.route('/customers', methods=['GET'])
@token_required
@tenant_scoped
def list_customers():
    """Get all customers for the current tenant"""
    try:
        customers = Customer.query.filter_by(
            tenant_id=request.tenant_id
        ).order_by(Customer.created_at.desc()).all()
        
        return jsonify({
            'customers': [
                {
                    'id': c.id,
                    'name': c.name,
                    'phone': c.phone,
                    'email': c.email,
                    'total_spent': c.total_spent,
                    'order_count': c.order_count
                }
                for c in customers
            ]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/customers', methods=['POST'])
@token_required
@tenant_scoped
def create_customer():
    """Create a new customer"""
    try:
        data = request.get_json()
        
        customer = Customer(
            id=str(uuid.uuid4()),
            tenant_id=request.tenant_id,
            name=data.get('name'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'message': 'Customer created',
            'customer_id': customer.id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============= ORDER ENDPOINTS =============
@app.route('/orders', methods=['GET'])
@token_required
@tenant_scoped
def list_orders():
    """Get all orders for the current tenant"""
    try:
        orders = Order.query.filter_by(
            tenant_id=request.tenant_id
        ).order_by(Order.created_at.desc()).all()
        
        return jsonify({
            'orders': [
                {
                    'id': o.id,
                    'order_number': o.order_number,
                    'customer_id': o.customer_id,
                    'status': o.status,
                    'total_amount': o.total_amount,
                    'payment_status': o.payment_status,
                    'created_at': o.created_at.isoformat()
                }
                for o in orders
            ]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/orders', methods=['POST'])
@token_required
@tenant_scoped
def create_order():
    """Create a new order from a conversation"""
    try:
        data = request.get_json()
        
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        order = Order(
            id=str(uuid.uuid4()),
            tenant_id=request.tenant_id,
            conversation_id=data.get('conversation_id'),
            customer_id=data.get('customer_id'),
            order_number=order_number,
            status=data.get('status', 'enquiry'),
            items=data.get('items', []),
            total_amount=data.get('total_amount', 0.0),
            notes=data.get('notes')
        )
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            'message': 'Order created',
            'order_id': order.id,
            'order_number': order_number
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/orders/<order_id>', methods=['GET'])
@token_required
@tenant_scoped
def get_order(order_id):
    """Get order details"""
    try:
        order = TenantFilter.get_or_404(Order, order_id, request.tenant_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        return jsonify({
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'customer_id': order.customer_id,
                'status': order.status,
                'items': order.items,
                'total_amount': order.total_amount,
                'payment_status': order.payment_status,
                'created_at': order.created_at.isoformat()
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= WHATSAPP WEBHOOK =============
@app.route('/webhook/whatsapp', methods=['GET'])
def verify_whatsapp_webhook():
    """Webhook verification (required by Meta)"""
    verify_token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    expected_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'test_token')
    
    print(f"Webhook verification: verify_token={verify_token}, expected={expected_token}", flush=True)
    
    if verify_token == expected_token:
        return challenge
    return 'Invalid verify token', 403

@app.route('/webhook/whatsapp', methods=['POST'])
def receive_whatsapp_message():
    """Receive incoming WhatsApp message from Meta"""
    try:
        data = request.get_json()
        logger.info(f"Webhook received data: {data}")
        
        # Extract message from Meta's webhook payload
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                
                # Check if this is a message event
                messages = value.get('messages', [])
                logger.info(f"Found {len(messages)} messages in webhook")
                
                for message in messages:
                    phone_number = message.get('from')
                    message_text = message.get('text', {}).get('body', '')
                    message_id = message.get('id')
                    
                    logger.info(f"Processing message: id={message_id}, from={phone_number}, text={message_text}")
                    
                    # Get tenant from request headers (for now, use first tenant)
                    # In production, match phone to tenant
                    tenant = Tenant.query.first()
                    if not tenant:
                        logger.error("No tenant found!")
                        continue
                    
                    logger.info(f"Saving message to tenant: {tenant.id}")
                    
                    # Create conversation record
                    conversation = Conversation(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant.id,
                        external_id=message_id,
                        channel='whatsapp',
                        customer_phone=phone_number,
                        message_text=message_text,
                        message_direction='inbound',
                        status='open'
                    )
                    db.session.add(conversation)
                
                db.session.commit()
                logger.info("Messages committed to database")
        
        # Meta requires 200 response immediately
        return jsonify({'status': 'ok'}), 200
    
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ============= ERROR HANDLERS =============
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)