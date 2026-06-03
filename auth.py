from flask import jsonify, request
from functools import wraps
import jwt
from datetime import datetime, timedelta
from config import get_config

config = get_config()

def generate_token(user_id, tenant_id):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'tenant_id': tenant_id,
        'exp': datetime.utcnow() + config.JWT_ACCESS_TOKEN_EXPIRES,
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm='HS256')
    return token

def verify_token(token):
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Extract token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        
        # Inject tenant_id and user_id into request context
        request.tenant_id = payload['tenant_id']
        request.user_id = payload['user_id']
        
        return f(*args, **kwargs)
    
    return decorated
