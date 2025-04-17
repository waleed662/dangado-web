from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100))
    total_sales = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoices = db.relationship('Invoice', backref='customer', lazy=True)
    sales = db.relationship('Sale', backref='customer', lazy=True)
    
    def __repr__(self):
        return f'<Customer {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='Small')  # 'Big' or 'Small'
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)  # In units (dozens * 12)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='product', lazy=True)
    production_records = db.relationship('Production', backref='product', lazy=True)
    
    def __repr__(self):
        return f'<Product {self.product_name}>'

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoice_date = db.Column(db.Date, default=datetime.utcnow)
    total_amount = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    payment_status = db.Column(db.String(20), default='unpaid')  # 'paid', 'partial', 'unpaid'
    amount_paid = db.Column(db.Float, default=0)
    balance_due = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='invoice', lazy=True)
    payments = db.relationship('Payment', backref='invoice', lazy=True)
    discount_records = db.relationship('DiscountTracking', backref='invoice', lazy=True)
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)  # In units
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.Date, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Sale {self.id} - {self.product.product_name if self.product else "Unknown"}>'

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    payment_date = db.Column(db.Date, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.id} for Invoice {self.invoice_id}>'

class Production(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity_produced = db.Column(db.Integer, nullable=False)  # In units
    production_date = db.Column(db.Date, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Production {self.id} - {self.product.product_name if self.product else "Unknown"}>'

class DiscountTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    total_before_discount = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, nullable=False)
    total_after_discount = db.Column(db.Float, nullable=False)
    discount_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    customer = db.relationship('Customer', backref='discounts')
    
    def __repr__(self):
        return f'<Discount {self.id} for Invoice {self.invoice_id}>'

# Add to your existing models.py file

class MonthlyPurchase(db.Model):
    """Tracks customer purchases by category per month"""
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Big' or 'Small'
    total_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship
    customer = db.relationship('Customer', backref=db.backref('monthly_purchases', lazy='dynamic'))
    
    # Unique constraint to ensure one record per customer/month/category
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'year', 'month', 'category', name='unique_monthly_purchase'),
    )


class DiscountVoucher(db.Model):
    """Stores discount vouchers generated at the end of each month"""
    id = db.Column(db.Integer, primary_key=True)
    voucher_number = db.Column(db.String(20), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    purchase_amount = db.Column(db.Float, nullable=False)
    discount_percentage = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, nullable=False)
    is_applied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    applied_at = db.Column(db.DateTime, nullable=True)
    applied_to_invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)
    
    # Relationships
    customer = db.relationship('Customer', backref=db.backref('discount_vouchers', lazy='dynamic'))
    applied_to_invoice = db.relationship('Invoice', backref=db.backref('applied_vouchers', lazy='dynamic'))