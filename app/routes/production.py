from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import Product, Production
from app import db
from datetime import datetime

production = Blueprint('production', __name__)

@production.route('/production')
@login_required
def index():
    productions = Production.query.order_by(Production.production_date.desc()).all()
    return render_template('production/index.html', productions=productions)

@production.route('/production/create', methods=['GET', 'POST'])
@login_required
def create():
    products = Product.query.all()
    
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        quantity_dozens = int(request.form.get('quantity', 0))
        quantity = quantity_dozens * 12  # Convert to units
        date = datetime.strptime(request.form.get('date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date()
        
        if not product_id or quantity <= 0:
            flash('Please select a product and enter a valid quantity', 'danger')
            return render_template('production/create.html', products=products)
        
        # Create production record
        production_record = Production(
            product_id=product_id,
            quantity_produced=quantity,
            production_date=date
        )
        db.session.add(production_record)
        
        # Update product stock
        product = Product.query.get(product_id)
        if product:
            product.stock_quantity += quantity
        
        try:
            db.session.commit()
            flash('Production record added successfully', 'success')
            return redirect(url_for('production.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('production/create.html', products=products)

@production.route('/production/view/<int:id>')
@login_required
def view(id):
    production_record = Production.query.get_or_404(id)
    return render_template('production/view.html', production=production_record)