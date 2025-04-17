# app/routes/products.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import Customer
from app.models import Product, Sale, Customer  # Add Customer to this list
from app.models import Product, Sale, Production
from app import db
from sqlalchemy import func
from datetime import datetime, timedelta

products = Blueprint('products', __name__)

@products.route('/products')
@login_required
def index():
    products_list = Product.query.order_by(Product.product_name).all()
    return render_template('products/index.html', products=products_list)

@products.route('/products/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        category = request.form.get('category')
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock', 0)) * 12  # Convert dozens to units
        
        if not product_name:
            flash('Product name is required', 'danger')
            return render_template('products/create.html')
        
        product = Product(
            product_name=product_name,
            category=category,
            price=price,
            stock_quantity=stock
        )
        
        db.session.add(product)
        
        try:
            db.session.commit()
            flash('Product added successfully', 'success')
            return redirect(url_for('products.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating product: {str(e)}', 'danger')
    
    return render_template('products/create.html')

@products.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.product_name = request.form.get('product_name')
        product.category = request.form.get('category')
        product.price = float(request.form.get('price'))
        
        # Only update stock if provided
        stock_dozens = request.form.get('stock')
        if stock_dozens:
            product.stock_quantity = int(stock_dozens) * 12  # Convert dozens to units
        
        try:
            db.session.commit()
            flash('Product updated successfully', 'success')
            return redirect(url_for('products.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
    
    return render_template('products/edit.html', product=product)

@products.route('/products/view/<int:id>')
@login_required
def view(id):
    product = Product.query.get_or_404(id)
    
    # Get sales data
    today = datetime.today()
    first_day = datetime(today.year, today.month, 1).date()
    
    # This month's sales
    month_sales = db.session.query(func.sum(Sale.quantity_sold)).filter(
        Sale.product_id == id,
        Sale.sale_date >= first_day
    ).scalar() or 0
    
    # This month's production
    month_production = db.session.query(func.sum(Production.quantity_produced)).filter(
        Production.product_id == id,
        Production.production_date >= first_day
    ).scalar() or 0
    
    # Get monthly sales for chart
    months = []
    monthly_sales = []
    
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
        
        month_total = db.session.query(func.sum(Sale.quantity_sold)).filter(
            Sale.product_id == id,
            Sale.sale_date >= first_day,
            Sale.sale_date <= last_day
        ).scalar() or 0
        
        # Convert to dozens for display
        monthly_sales.append(float(month_total) / 12)
    
    # Get recent sales for this product
    recent_sales = db.session.query(
        Sale.sale_date,  # Make sure sale_date is included
        Sale.quantity_sold,
        Sale.unit_price,
        Sale.total_price,
        Customer.name.label('customer_name')  # Alias customer name
    ).join(
        Customer
    ).filter(
        Sale.product_id == id
    ).order_by(
        Sale.sale_date.desc()
    ).limit(10).all()
    
    # Get recent production entries
    productions = Production.query.filter_by(product_id=id).order_by(Production.created_at.desc()).limit(10).all()
    
    
    return render_template(
        'products/view.html', 
        recent_sales=recent_sales,
        product=product,
        month_sales=month_sales // 12,  # Convert to dozens
        month_production=month_production // 12,  # Convert to dozens
        months=months,
        monthly_sales=monthly_sales,
        productions=productions  # Removed the sales=sales line
    )
@products.route('/products/adjust/<int:id>', methods=['GET', 'POST'])
@login_required
def adjust_stock(id):
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            adjustment_type = request.form.get('type')
            quantity_dozens = int(request.form.get('quantity', 0))
            quantity = quantity_dozens * 12  # Convert to units
            
            if adjustment_type == 'add':
                # Add to stock (production)
                production = Production(
                    product_id=id,
                    quantity_produced=quantity,
                    production_date=datetime.now().date()
                )
                db.session.add(production)
                
                product.stock_quantity += quantity
                message = f'Added {quantity_dozens} dozens to stock'
            else:
                # Remove from stock (adjustment)
                if product.stock_quantity < quantity:
                    flash(f'Not enough stock. Current stock: {product.stock_quantity // 12} dozens', 'danger')
                    return redirect(url_for('products.adjust_stock', id=id))
                    
                product.stock_quantity -= quantity
                message = f'Removed {quantity_dozens} dozens from stock'
            
            db.session.commit()
            flash(message, 'success')
            return redirect(url_for('products.view', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adjusting stock: {str(e)}', 'danger')
    
    return render_template('products/adjust_stock.html', product=product)