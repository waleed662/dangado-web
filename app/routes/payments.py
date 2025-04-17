from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required
from app.models import Payment, Invoice, Customer
from app import db
from app.utils import generate_receipt_pdf
from datetime import datetime

payments = Blueprint('payments', __name__)

@payments.route('/payments')
@login_required
def index():
    payments = Payment.query.order_by(Payment.payment_date.desc()).all()
    return render_template('payments/index.html', payments=payments)

@payments.route('/payments/create/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def create(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.payment_status == 'paid':
        flash('This invoice is already fully paid', 'warning')
        return redirect(url_for('invoices.view', id=invoice_id))
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        payment_date = datetime.strptime(request.form.get('payment_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date()
        payment_method = request.form.get('payment_method', 'Cash')
        notes = request.form.get('notes', '')
        
        if amount <= 0:
            flash('Payment amount must be greater than zero', 'danger')
            return render_template('payments/create.html', invoice=invoice)
        
        if amount > invoice.balance_due:
            flash(f'Payment amount (₦{amount:,.2f}) exceeds balance due (₦{invoice.balance_due:,.2f})', 'danger')
            return render_template('payments/create.html', invoice=invoice)
        
        # Create payment record
        payment = Payment(
            invoice_id=invoice_id,
            payment_date=payment_date,
            amount_paid=amount,
            payment_method=payment_method,
            notes=notes
        )
        db.session.add(payment)
        
        # Update invoice
        invoice.amount_paid += amount
        invoice.balance_due -= amount
        
        if invoice.balance_due <= 0:
            invoice.payment_status = 'paid'
        else:
            invoice.payment_status = 'partial'
        
        try:
            db.session.commit()
            flash('Payment recorded successfully', 'success')
            return redirect(url_for('invoices.view', id=invoice_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('payments/create.html', invoice=invoice)

@payments.route('/payments/view/<int:id>')
@login_required
def view(id):
    payment = Payment.query.get_or_404(id)
    return render_template('payments/view.html', payment=payment)

@payments.route('/payments/receipt/<int:id>')
@login_required
def receipt(id):
    payment = Payment.query.get_or_404(id)
    
    pdf_buffer = generate_receipt_pdf(payment)
    pdf_buffer.seek(0)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Receipt_{payment.id}.pdf'
    )