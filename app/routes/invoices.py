from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from app.models import Invoice, Customer, Product, Sale, Payment, DiscountTracking
from app import db
from app.utils import generate_invoice_pdf, check_discount_eligibility
from app.utils import update_monthly_purchases
from datetime import datetime
import io
import json

invoices = Blueprint('invoices', __name__)

@invoices.route('/invoices')
@login_required
def index():
    invoices_list = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template('invoices/index.html', invoices=invoices_list)

@invoices.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def create():
    customers = Customer.query.all()
    products = Product.query.all()
    
    if request.method == 'POST':
        try:
            data = json.loads(request.data)
            customer_id = data.get('customer_id')
            items = data.get('items')
            notes = data.get('notes', '')
            
            # Validate data
            if not customer_id or not items or len(items) == 0:
                return jsonify({'success': False, 'message': 'Missing required data'})
            
            customer = Customer.query.get(customer_id)
            if not customer:
                return jsonify({'success': False, 'message': 'Customer not found'})
            
            # Generate invoice number (INV-YYYYMMDD-XXX format)
            date_part = datetime.now().strftime('%Y%m%d')
            last_invoice = Invoice.query.filter(
                Invoice.invoice_number.like(f'INV-{date_part}-%')
            ).order_by(Invoice.id.desc()).first()
            
            if last_invoice:
                try:
                    last_num = int(last_invoice.invoice_number.split('-')[-1])
                    invoice_num = f'INV-{date_part}-{last_num + 1:03d}'
                except:
                    invoice_num = f'INV-{date_part}-001'
            else:
                invoice_num = f'INV-{date_part}-001'
            
            # Create invoice
            invoice = Invoice(
                invoice_number=invoice_num,
                customer_id=customer_id,
                invoice_date=datetime.now().date(),
                notes=notes,
                payment_status='unpaid'
            )
            
            db.session.add(invoice)
            db.session.flush()  # Get ID without committing yet
            
            total_amount = 0
            
            # Process items (no discount calculation)
            for item in items:
                product_id = item.get('product_id')
                quantity = int(item.get('quantity', 0))  # In dozens
                
                # Convert dozens to units
                quantity_units = quantity * 12
                
                product = Product.query.get(product_id)
                if not product:
                    return jsonify({'success': False, 'message': f'Product ID {product_id} not found'})
                
                if product.stock_quantity < quantity_units:
                    return jsonify({
                        'success': False, 
                        'message': f'Insufficient stock for {product.product_name}. ' + 
                                  f'Available: {product.stock_quantity // 12} dozens'
                    })
                
                # Calculate prices (no discount)
                price_per_dozen = product.price
                item_total = price_per_dozen * quantity
                
                # Create sale record
                sale = Sale(
                    invoice_id=invoice.id,
                    customer_id=customer_id,
                    product_id=product_id,
                    quantity_sold=quantity_units,
                    unit_price=price_per_dozen,
                    total_price=item_total,
                    sale_date=datetime.now().date()
                )
                
                db.session.add(sale)
                
                # Update product stock
                product.stock_quantity -= quantity_units
                
                # Update total
                total_amount += item_total
            
            # Update invoice with total
            invoice.total_amount = total_amount
            invoice.balance_due = total_amount
            
            # Update customer total sales
            customer.total_sales += total_amount
            
            db.session.commit()
            
            # Update monthly purchases after invoice is created
            update_monthly_purchases(invoice.id)
            
            return jsonify({
                'success': True, 
                'invoice_id': invoice.id,
                'message': 'Invoice created successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})
    
    return render_template('invoices/create.html', customers=customers, products=products)

@invoices.route('/invoices/view/<int:id>')
@login_required
def view(id):
    invoice = Invoice.query.get_or_404(id)
    sales = Sale.query.filter_by(invoice_id=id).all()
    payments = Payment.query.filter_by(invoice_id=id).all()
    
    # Check if discount was applied
    discount = DiscountTracking.query.filter_by(invoice_id=id).first()
    
    return render_template('invoices/view.html', 
                           invoice=invoice, 
                           sales=sales, 
                           payments=payments,
                           discount=discount)

@invoices.route('/invoices/generate-pdf/<int:id>')
@login_required
def generate_pdf(id):
    invoice = Invoice.query.get_or_404(id)
    sales = Sale.query.filter_by(invoice_id=id).all()
    discount = DiscountTracking.query.filter_by(invoice_id=id).first()
    
    pdf_buffer = generate_invoice_pdf(invoice, sales, discount)
    pdf_buffer.seek(0)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Invoice_{invoice.invoice_number}.pdf"
    )