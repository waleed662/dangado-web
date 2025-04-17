from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import Sale, Product, Customer
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func

sales = Blueprint('sales', __name__)

@sales.route('/sales')
@login_required
def index():
    # Default to current month
    today = datetime.now()
    first_day = today.replace(day=1).strftime('%Y-%m-%d')
    
    from_date = request.args.get('from_date', first_day)
    to_date = request.args.get('to_date', today.strftime('%Y-%m-%d'))
    customer_id = request.args.get('customer_id', 'all')
    
    # Build query
    query = Sale.query.filter(
        Sale.sale_date >= from_date,
        Sale.sale_date <= to_date
    )
    
    if customer_id != 'all' and customer_id.isdigit():
        query = query.filter(Sale.customer_id == int(customer_id))
    
    sales = query.order_by(Sale.sale_date.desc()).all()
    
    # Get customers for filter dropdown
    customers = Customer.query.all()
    
    return render_template(
        'sales/index.html',
        sales=sales,
        customers=customers,
        from_date=from_date,
        to_date=to_date,
        selected_customer=customer_id
    )

@sales.route('/sales/create', methods=['GET', 'POST'])
@login_required
def create():
    customers = Customer.query.all()
    products = Product.query.all()
    
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        product_id = request.form.get('product_id')
        quantity_dozens = int(request.form.get('quantity', 0))
        quantity = quantity_dozens * 12  # Convert to units
        date = datetime.strptime(request.form.get('date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date()
        
        if not customer_id or not product_id or quantity <= 0:
            flash('Please fill in all required fields', 'danger')
            return render_template('sales/create.html', customers=customers, products=products)
        
        # Get product details
        product = Product.query.get(product_id)
        if not product:
            flash('Selected product not found', 'danger')
            return render_template('sales/create.html', customers=customers, products=products)
        
        # Check stock
        if product.stock_quantity < quantity:
            flash(f'Insufficient stock. Only {product.stock_quantity // 12} dozens available', 'danger')
            return render_template('sales/create.html', customers=customers, products=products)
        
        # Calculate totals
        unit_price = product.price
        total_price = unit_price * quantity
        
        # Create sale record
        sale = Sale(
            customer_id=customer_id,
            product_id=product_id,
            quantity_sold=quantity,
            unit_price=unit_price,
            total_price=total_price,
            sale_date=date
        )
        db.session.add(sale)
        
        # Update product stock
        product.stock_quantity -= quantity
        
        # Update customer total sales
        customer = Customer.query.get(customer_id)
        if customer:
            customer.total_sales += total_price
        
        try:
            db.session.commit()
            flash('Sale recorded successfully', 'success')
            return redirect(url_for('sales.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('sales/create.html', customers=customers, products=products)

@sales.route('/sales/view/<int:id>')
@login_required
def view(id):
    sale = Sale.query.get_or_404(id)
    return render_template('sales/view.html', sale=sale)