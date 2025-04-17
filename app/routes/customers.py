# app/routes/customers.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import Customer, Invoice, Sale
from app import db
from sqlalchemy import func
from datetime import datetime, timedelta

customers = Blueprint('customers', __name__)

@customers.route('/customers')
@login_required
def index():
    customers_list = Customer.query.order_by(Customer.name).all()
    return render_template('customers/index.html', customers=customers_list)

@customers.route('/customers/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact')
        
        if not name:
            flash('Customer name is required', 'danger')
            return render_template('customers/create.html')
        
        customer = Customer(name=name, contact=contact)
        db.session.add(customer)
        
        try:
            db.session.commit()
            flash('Customer added successfully', 'success')
            return redirect(url_for('customers.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating customer: {str(e)}', 'danger')
    
    return render_template('customers/create.html')

@customers.route('/customers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.contact = request.form.get('contact')
        
        try:
            db.session.commit()
            flash('Customer updated successfully', 'success')
            return redirect(url_for('customers.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'danger')
    
    return render_template('customers/edit.html', customer=customer)

@customers.route('/customers/view/<int:id>')
@login_required
def view(id):
    customer = Customer.query.get_or_404(id)
    
    # Get recent invoices
    invoices = Invoice.query.filter_by(customer_id=id).order_by(Invoice.created_at.desc()).limit(10).all()
    
    # Check discount eligibility
    from app.utils import check_discount_eligibility
    discount_info = check_discount_eligibility(id)
    
    # Calculate stats
    total_invoices = Invoice.query.filter_by(customer_id=id).count()
    unpaid_invoices = Invoice.query.filter_by(customer_id=id, payment_status='unpaid').count()
    
    # Get monthly purchase data for chart
    months = []
    monthly_data = []
    
    today = datetime.today()
    for i in range(5, -1, -1):
        if today.month - i <= 0:
            month_num = today.month - i + 12
            year = today.year - 1
        else:
            month_num = today.month - i
            year = today.year
            
        month_name = datetime(year, month_num, 1).strftime('%b %Y')
        months.append(month_name)
        
        first_day = datetime(year, month_num, 1).date()
        if month_num == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month_num + 1, 1).date() - timedelta(days=1)
        
        month_total = db.session.query(func.sum(Sale.total_price)).filter(
            Sale.customer_id == id,
            Sale.sale_date >= first_day,
            Sale.sale_date <= last_day
        ).scalar() or 0
        
        monthly_data.append(float(month_total))
    
    return render_template(
        'customers/view.html', 
        customer=customer, 
        invoices=invoices, 
        discount_info=discount_info,
        total_invoices=total_invoices,
        unpaid_invoices=unpaid_invoices,
        months=months,
        monthly_data=monthly_data
    )

@customers.route('/customers/statement/<int:id>')
@login_required
def statement(id):
    customer = Customer.query.get_or_404(id)
    
    # Get date range parameters
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    if not from_date:
        # Default to first day of current month
        today = datetime.today()
        from_date = datetime(today.year, today.month, 1).strftime('%Y-%m-%d')
        
    if not to_date:
        # Default to today
        to_date = datetime.today().strftime('%Y-%m-%d')
    
    # Get invoices for the period
    invoices = Invoice.query.filter(
        Invoice.customer_id == id,
        Invoice.invoice_date >= from_date,
        Invoice.invoice_date <= to_date
    ).order_by(Invoice.invoice_date).all()
    
    # Calculate totals
    total_purchases = sum(invoice.total_amount for invoice in invoices)
    total_paid = sum(invoice.amount_paid for invoice in invoices)
    total_balance = sum(invoice.balance_due for invoice in invoices)
    
    return render_template(
        'customers/statement.html',
        customer=customer,
        invoices=invoices,
        from_date=from_date,
        to_date=to_date,
        total_purchases=total_purchases,
        total_paid=total_paid,
        total_balance=total_balance
    )