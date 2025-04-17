from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import Customer, MonthlyPurchase, DiscountVoucher, Invoice
from app import db
from app.utils import generate_monthly_discounts, apply_voucher_to_invoice
from datetime import datetime
import calendar

discounts = Blueprint('discounts', __name__)

@discounts.route('/discounts')
@login_required
def index():
    """Show discount management dashboard"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get counts
    total_vouchers = DiscountVoucher.query.count()
    applied_vouchers = DiscountVoucher.query.filter_by(is_applied=True).count()
    unapplied_vouchers = total_vouchers - applied_vouchers
    
    # Get current month's data
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Get monthly purchases above threshold
    eligible_purchases = MonthlyPurchase.query.filter(
        MonthlyPurchase.year == current_year,
        MonthlyPurchase.month == current_month,
        MonthlyPurchase.total_amount >= 1000000
    ).all()
    
    return render_template('discounts/index.html',
                          total_vouchers=total_vouchers,
                          applied_vouchers=applied_vouchers,
                          unapplied_vouchers=unapplied_vouchers,
                          eligible_purchases=eligible_purchases,
                          current_month=calendar.month_name[current_month],
                          current_year=current_year,
                          calendar=calendar,  # Pass the calendar module to the template
                          now=datetime.now())


@discounts.route('/discounts/vouchers')
@login_required
def vouchers():
    """Show all discount vouchers"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get filter parameters
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    status = request.args.get('status', '')
    
    # Build query
    query = DiscountVoucher.query
    
    if year and month:
        query = query.filter(DiscountVoucher.year == year, DiscountVoucher.month == month)
    
    if status == 'applied':
        query = query.filter(DiscountVoucher.is_applied == True)
    elif status == 'unapplied':
        query = query.filter(DiscountVoucher.is_applied == False)
    
    # Get vouchers
    vouchers = query.order_by(DiscountVoucher.created_at.desc()).all()
    
    return render_template('discounts/vouchers.html',
                          vouchers=vouchers,
                          year=year,
                          month=month,
                          status=status,
                          calendar=calendar,  # Add this
                          now=datetime.now())

@discounts.route('/discounts/monthly-purchases')
@login_required
def monthly_purchases():
    """Show monthly purchase data"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get filter parameters
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # Get all customers
    customers = Customer.query.all()
    
    # Get monthly purchase data
    purchases = MonthlyPurchase.query.filter_by(
        year=year,
        month=month
    ).order_by(MonthlyPurchase.total_amount.desc()).all()
    
    return render_template('discounts/monthly_purchases.html',
                          purchases=purchases,
                          customers=customers,
                          year=year,
                          month=month,
                          month_name=calendar.month_name[month],
                          calendar=calendar,
                          now=datetime.now())  # Add this line

@discounts.route('/discounts/generate', methods=['POST'])
@login_required
def generate():
    """Generate discount vouchers for a specific month"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    year = request.form.get('year', type=int)
    month = request.form.get('month', type=int)
    
    if not year or not month:
        flash('Invalid year or month specified.', 'danger')
        return redirect(url_for('discounts.index'))
    
    # Generate discount vouchers
    vouchers_generated = generate_monthly_discounts(year, month)
    
    flash(f'Successfully generated {vouchers_generated} discount vouchers.', 'success')
    return redirect(url_for('discounts.vouchers', year=year, month=month))

@discounts.route('/discounts/customer/<int:id>')
@login_required
def customer_discounts(id):
    """Show discount history for a specific customer"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    customer = Customer.query.get_or_404(id)
    
    # Get monthly purchases
    purchases = MonthlyPurchase.query.filter_by(
        customer_id=id
    ).order_by(MonthlyPurchase.year.desc(), MonthlyPurchase.month.desc()).all()
    
    # Get discount vouchers
    vouchers = DiscountVoucher.query.filter_by(
        customer_id=id
    ).order_by(DiscountVoucher.created_at.desc()).all()
    
    return render_template('discounts/customer.html',
                          customer=customer,
                          purchases=purchases,
                          vouchers=vouchers)

@discounts.route('/discounts/apply-voucher', methods=['POST'])
@login_required
def apply_voucher():
    """Apply a discount voucher to an invoice"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    voucher_id = request.form.get('voucher_id', type=int)
    invoice_id = request.form.get('invoice_id', type=int)
    
    if not voucher_id or not invoice_id:
        return jsonify({'success': False, 'message': 'Missing required parameters'})
    
    # Apply voucher
    result = apply_voucher_to_invoice(voucher_id, invoice_id)
    
    if result:
        return jsonify({'success': True, 'message': 'Voucher applied successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to apply voucher'})