from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Product, Customer, Invoice, Sale, Payment
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/')
@dashboard.route('/dashboard')
@login_required
def index():
    # Product count
    product_count = Product.query.count()
    
    # Customer count
    customer_count = Customer.query.count()
    
    # Low stock items (less than 10 dozens)
    low_stock = Product.query.filter(Product.stock_quantity < 120).all()
    
    # Monthly sales
    today = datetime.today()
    first_day_of_month = datetime(today.year, today.month, 1)
    
    monthly_sales = db.session.query(
        func.sum(Sale.total_price)
    ).filter(
        Sale.sale_date >= first_day_of_month
    ).scalar() or 0
    
    # Recent invoices
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    # Sales chart data (last 7 days)
    last_7_days = []
    sales_data = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        last_7_days.append(date.strftime('%d-%b'))
        
        day_sales = db.session.query(
            func.sum(Sale.total_price)
        ).filter(
            func.date(Sale.sale_date) == date.date()
        ).scalar() or 0
        
        sales_data.append(day_sales)
    
    # Top products
    top_products = db.session.query(
        Product.product_name,
        func.sum(Sale.total_price).label('total_sales')
    ).join(Sale).group_by(Product.id).order_by(func.sum(Sale.total_price).desc()).limit(5).all()
    
    product_labels = [p[0] for p in top_products]
    product_values = [float(p[1]) for p in top_products]
    
    return render_template(
        'dashboard/index.html',
        product_count=product_count,
        customer_count=customer_count,
        low_stock=low_stock,
        monthly_sales=monthly_sales,
        recent_invoices=recent_invoices,
        last_7_days=last_7_days,
        sales_data=sales_data,
        product_labels=product_labels,
        product_values=product_values
    )