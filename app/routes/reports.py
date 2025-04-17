from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from app.models import Sale, Invoice, Customer, Product, Payment
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from io import BytesIO
import calendar
import matplotlib.pyplot as plt
import numpy as np

reports = Blueprint('reports', __name__)

@reports.route('/reports')
@login_required
def index():
    return render_template('reports/index.html')

@reports.route('/reports/sales')
@login_required
def sales_report():
    # Get request parameters
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    
    # Define month_names list
    month_names = [calendar.month_name[i] for i in range(1, 13)]
    
    # Get first and last day of selected month
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    
    # Get sales data for the month including category
    sales_data = db.session.query(
        Product.product_name,
        Product.category,  # Add category to query
        func.sum(Sale.quantity_sold).label('quantity'),
        func.sum(Sale.total_price).label('revenue')
    ).join(Sale).filter(
        Sale.sale_date >= first_day,
        Sale.sale_date <= last_day
    ).group_by(Product.id, Product.category).order_by(func.sum(Sale.total_price).desc()).all()
    
    # Calculate total sales for the month
    total_sales = db.session.query(func.sum(Sale.total_price)).filter(
        Sale.sale_date >= first_day,
        Sale.sale_date <= last_day
    ).scalar() or 0
    
    # Calculate category sales for the pie chart
    big_category_sales = 0
    small_category_sales = 0
    for product in sales_data:
        if product.category == 'Big':
            big_category_sales += product.revenue
        elif product.category == 'Small':
            small_category_sales += product.revenue
    
    # Get top customers for this month
    customer_sales = db.session.query(
        Customer.id,
        Customer.name,
        func.count(Invoice.id).label('orders'),
        func.sum(Invoice.total_amount).label('amount')
    ).join(Invoice).filter(
        Invoice.invoice_date >= first_day,
        Invoice.invoice_date <= last_day
    ).group_by(Customer.id).order_by(func.sum(Invoice.total_amount).desc()).limit(5).all()
    
    top_customers = []
    for customer in customer_sales:
        top_customers.append({
            'name': customer.name,
            'orders': customer.orders,
            'amount': customer.amount
        })
    
    # Get all customers for filter dropdown
    customers = Customer.query.order_by(Customer.name).all()
    
    # Get daily sales for chart
    days_in_month = calendar.monthrange(year, month)[1]
    daily_sales = []
    
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day).date()
        
        daily_total = db.session.query(func.sum(Sale.total_price)).filter(
            Sale.sale_date == date
        ).scalar() or 0
        
        daily_sales.append((date.strftime('%d-%b'), float(daily_total)))
    
    return render_template(
        'reports/sales_report.html',
        sales_data=sales_data,
        total_sales=total_sales,
        year=year,
        month=month,
        month_name=calendar.month_name[month],
        daily_sales=daily_sales,
        month_names=month_names,
        big_category_sales=big_category_sales,
        small_category_sales=small_category_sales,
        top_customers=top_customers,
        customers=customers,
        calendar=calendar,
        now=datetime.now()
    )


@reports.route('/reports/inventory')
@login_required
def inventory_report():
    products = Product.query.order_by(Product.category, Product.product_name).all()
    
    # Calculate stock value for each product
    for product in products:
        product.stock_value = product.price * product.stock_quantity
    
    # Group products by category
    categories = {}
    for product in products:
        if product.category not in categories:
            categories[product.category] = []
        categories[product.category].append(product)
    
    return render_template(
        'reports/inventory_report.html',
        products=products,
        categories=categories,
        now=datetime.now()
    )

@reports.route('/reports/customers')
@login_required
def customer_report():
    # First define current_month
    current_month = datetime.now().replace(day=1).date()
    
    # Get top customers by sales
    top_customers = Customer.query.order_by(Customer.total_sales.desc()).limit(10).all()
    
    # Get current month customers
    month_invoices = db.session.query(
        Customer.id,
        Customer.name,
        func.sum(Invoice.total_amount).label('month_total')
    ).join(Invoice).filter(
        Invoice.invoice_date >= current_month
    ).group_by(Customer.id).order_by(func.sum(Invoice.total_amount).desc()).limit(10).all()
    
    # Calculate total month sales
    month_total = db.session.query(func.sum(Invoice.total_amount)).filter(
        Invoice.invoice_date >= current_month
    ).scalar() or 0
    
    # Calculate number of active customers this month
    active_customers_count = db.session.query(func.count(func.distinct(Invoice.customer_id))).filter(
        Invoice.invoice_date >= current_month
    ).scalar() or 0
    
    # Calculate average per customer
    month_average = month_total / active_customers_count if active_customers_count > 0 else 0
    
    # Calculate discount eligible count (customers with purchases over 1,000,000)
    discount_eligible_count = db.session.query(func.count(func.distinct(Invoice.customer_id))).filter(
        Invoice.invoice_date >= current_month,
        Invoice.total_amount >= 1000000
    ).scalar() or 0
    
    return render_template(
        'reports/customer_report.html',
        top_customers=top_customers,
        month_invoices=month_invoices,
        current_month=datetime.now().strftime('%B %Y'),
        month_total=month_total,
        month_average=month_average,  # Add this line
        discount_eligible_count=discount_eligible_count,  # Add this if your template uses it
        now=datetime.now(),
        total_customers=Customer.query.count()  # Add this if your template needs it
    )

@reports.route('/reports/generate_chart/<report_type>')
@login_required
def generate_chart(report_type):
    if report_type == 'monthly_sales':
        # Generate monthly sales chart for current year
        year = datetime.now().year
        months = []
        sales = []
        
        for month in range(1, 13):
            first_day = datetime(year, month, 1).date()
            if month == 12:
                last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            month_sales = db.session.query(func.sum(Sale.total_price)).filter(
                Sale.sale_date >= first_day,
                Sale.sale_date <= last_day
            ).scalar() or 0
            
            months.append(calendar.month_abbr[month])
            sales.append(float(month_sales))
        
        # Create chart
        plt.figure(figsize=(10, 6))
        plt.bar(months, sales, color='#0066cc')
        plt.title(f'Monthly Sales for {year}')
        plt.xlabel('Month')
        plt.ylabel('Sales (₦)')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Format y-axis with commas
        plt.gca().get_yaxis().set_major_formatter(
            plt.matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ','))
        )
        
        # Save chart to BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        return send_file(img_buffer, mimetype='image/png')
    
    return "Chart type not supported", 400

@reports.route('/reports/payment')
@login_required
def payment_report():
    # Get filter parameters
    from_date = request.args.get('from_date', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', datetime.now().strftime('%Y-%m-%d'))
    payment_method = request.args.get('payment_method', '')
    customer_id = request.args.get('customer_id', '')
    
    # Query customers for filter dropdown
    customers = Customer.query.order_by(Customer.name).all()
    
    # Base query for payments
    query = Payment.query.join(Invoice).join(Customer)
    
    # Apply filters
    if from_date:
        query = query.filter(Payment.payment_date >= from_date)
    if to_date:
        query = query.filter(Payment.payment_date <= to_date)
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    if customer_id:
        query = query.filter(Invoice.customer_id == int(customer_id))
    
    # Get payments and calculate totals
    payments = query.order_by(Payment.payment_date.desc()).all()
    total_amount = sum(payment.amount_paid for payment in payments)
    
    # Analyze payment methods
    payment_methods = []
    method_counts = {}
    
    for payment in payments:
        method = payment.payment_method
        if method not in method_counts:
            method_counts[method] = {'count': 0, 'amount': 0}
        
        method_counts[method]['count'] += 1
        method_counts[method]['amount'] += payment.amount_paid
    
    for method, data in method_counts.items():
        percentage = (data['amount'] / total_amount * 100) if total_amount > 0 else 0
        payment_methods.append({
            'name': method,
            'count': data['count'],
            'amount': data['amount'],
            'percentage': percentage
        })
    
    # Sort payment methods by amount (descending)
    payment_methods.sort(key=lambda x: x['amount'], reverse=True)
    
    return render_template(
        'reports/payment_report.html',
        from_date=from_date,
        to_date=to_date,
        customers=customers,
        payments=payments,
        total_amount=total_amount,
        payment_methods=payment_methods,
        now=datetime.now()
    )

@reports.route('/reports/discount')
@login_required
def discount_report():
    # Get filter parameters
    from_date = request.args.get('from_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', datetime.now().strftime('%Y-%m-%d'))
    customer_id = request.args.get('customer_id', '')
    
    # Query customers for filter dropdown
    customers = Customer.query.order_by(Customer.name).all()
    
    # Since we don't have discount_percentage, let's just get all invoices
    # and filter them later if needed
    query = Invoice.query.join(Customer)
    
    # Apply date and customer filters
    if from_date:
        query = query.filter(Invoice.invoice_date >= from_date)
    if to_date:
        query = query.filter(Invoice.invoice_date <= to_date)
    if customer_id:
        query = query.filter(Invoice.customer_id == int(customer_id))
    
    # Get orders
    orders = query.order_by(Invoice.invoice_date.desc()).all()
    
    # Placeholder values - you'll need to adjust these based on your actual data structure
    total_orders = len(orders)
    total_discount_amount = 0  # You'll need to calculate this based on your data
    total_original_value = sum(order.total_amount for order in orders)
    avg_discount_rate = 0  # Placeholder
    
    # Get sales representatives for filter dropdown
    sales_reps = []  # Replace with actual data if available
    
    return render_template(
        'reports/discount_report.html',
        from_date=from_date,
        to_date=to_date,
        customers=customers,
        sales_reps=sales_reps,
        orders=orders,
        total_orders=total_orders,
        total_discount_amount=total_discount_amount,
        total_original_value=total_original_value,
        avg_discount_rate=avg_discount_rate,
        min_discount='',
        max_discount='',
        customer_id=customer_id,
        sales_rep='',
        now=datetime.now()
    )

@reports.route('/reports/production')
@login_required
def production_report():
    # This is a placeholder implementation
    # You'll need to adapt this to your actual production model and data structure
    
    # Get filter parameters
    from_date = request.args.get('from_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', datetime.now().strftime('%Y-%m-%d'))
    
    return render_template(
        'reports/production_report.html',
        from_date=from_date,
        to_date=to_date,
        production_data=[],  # Replace with actual production data
        now=datetime.now()
    )