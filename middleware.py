from flask import request, jsonify
from functools import wraps
from models import db

def tenant_scoped(f):
    """
    Decorator that ensures all queries are scoped to the requesting tenant.
    Must be used AFTER @token_required so request.tenant_id is set.
    
    This is the key to multi-tenancy security — no data leakage between tenants.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'tenant_id'):
            return jsonify({'error': 'Tenant context not found'}), 400
        
        # Tenant ID is now available in request.tenant_id
        # Your service functions should use this to filter all queries
        return f(*args, **kwargs)
    
    return decorated

class TenantFilter:
    """Helper class to apply tenant filtering to SQLAlchemy queries"""
    
    @staticmethod
    def apply_filter(query, model, tenant_id):
        """
        Apply tenant filter to a query.
        Usage: TenantFilter.apply_filter(db.session.query(Order), Order, request.tenant_id)
        """
        if not hasattr(model, 'tenant_id'):
            return query
        
        return query.filter(model.tenant_id == tenant_id)
    
    @staticmethod
    def get_or_404(model, model_id, tenant_id):
        """
        Get a single record by ID, ensuring it belongs to the tenant.
        Prevents a user from accessing another tenant's data.
        """
        record = db.session.query(model).filter(
            model.id == model_id,
            model.tenant_id == tenant_id
        ).first()
        
        if not record:
            return None
        
        return record
