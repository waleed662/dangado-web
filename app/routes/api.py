# Add to a new file api.py or to an existing api routes file

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models import Customer, Invoice, DiscountVoucher
from app import db
from datetime import datetime

api = Blueprint('api', __name__)

@api.route('/api/customer/<int:customer_id>/unpaid-invoices')
@login_required
def get_customer_unpaid_invoices(customer_id):
    """Get unpaid invoices for a specific customer - used for applying discount vouchers"""
    customer = Customer.query.get_or_404(customer_id)
    
    # Get all unpaid invoices for this customer
    invoices = Invoice.query.filter_by(
        customer_id=customer_id,
        payment_status='unpaid'
    ).order_by(Invoice.invoice_date.desc()).all()
    
    invoice_list = []
    
    for invoice in invoices:
        invoice_list.append({
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d'),
            'total_amount': float(invoice.total_amount),
            'balance_due': float(invoice.balance_due)
        })
    
    return jsonify({
        'success': True,
        'customer_id': customer_id,
        'customer_name': customer.name,
        'invoices': invoice_list
    })