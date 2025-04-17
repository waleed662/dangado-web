from io import BytesIO
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas
from app import db
from sqlalchemy import func
from app.models import Sale, Invoice, Customer, Product, Payment, MonthlyPurchase, DiscountVoucher
from app import db
from datetime import datetime
import calendar
from sqlalchemy import func, extract
import random
import string

def check_discount_eligibility(customer_id):
    """Check if a customer is eligible for discount based on monthly purchases"""
    from app.models import Sale
    
    # Get current month
    today = datetime.today()
    first_day = datetime(today.year, today.month, 1).date()
    
    # If we're in the first few days of the month, also check previous month
    include_prev_month = today.day < 5
    
    # Calculate total for current month
    current_month_total = db.session.query(func.sum(Sale.total_price)).filter(
        Sale.customer_id == customer_id,
        Sale.sale_date >= first_day
    ).scalar() or 0
    
    monthly_total = current_month_total
    
    # Check previous month if needed
    if include_prev_month:
        if today.month == 1:
            prev_month_start = datetime(today.year - 1, 12, 1).date()
        else:
            prev_month_start = datetime(today.year, today.month - 1, 1).date()
            
        prev_month_end = first_day - timedelta(days=1)
        
        prev_month_total = db.session.query(func.sum(Sale.total_price)).filter(
            Sale.customer_id == customer_id,
            Sale.sale_date >= prev_month_start,
            Sale.sale_date <= prev_month_end
        ).scalar() or 0
        
        # Use the higher of the two months
        monthly_total = max(current_month_total, prev_month_total)
    
    # Check if total exceeds discount threshold (₦1,000,000)
    discount_eligible = monthly_total >= 1000000
    
    return {
        'eligible': discount_eligible,
        'monthly_total': monthly_total
    }

def generate_invoice_pdf(invoice, sales, discount=None):
    """Generate PDF for an invoice"""
    buffer = BytesIO()
    
    # Set up the PDF
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Set brand blue color
    brand_blue = HexColor('#0066cc')
    
    # Add company header
    c.setFillColor(brand_blue)
    c.rect(0, height - 60, width, 60, fill=True)
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(72, height - 35, "DANGADO PLASTICS LTD.")
    
    # Add invoice title
    c.setFillColor(HexColor('#000000'))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 100, "INVOICE")
    
    # Add invoice information
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, height - 130, f"Invoice #: {invoice.invoice_number}")
    c.drawString(72, height - 150, f"Date: {invoice.invoice_date.strftime('%Y-%m-%d')}")
    
    # Customer information
    c.drawString(72, height - 180, "Bill To:")
    c.setFont("Helvetica", 12)
    c.drawString(150, height - 180, invoice.customer.name)
    c.drawString(150, height - 200, invoice.customer.contact or "")
    
    # Payment status
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, height - 130, "Status:")
    
    # Color status based on payment status
    if invoice.payment_status == 'paid':
        c.setFillColor(HexColor('#009900'))  # Green
    elif invoice.payment_status == 'partial':
        c.setFillColor(HexColor('#FF9900'))  # Orange
    else:
        c.setFillColor(HexColor('#CC0000'))  # Red
        
    c.drawString(450, height - 130, invoice.payment_status.upper())
    c.setFillColor(HexColor('#000000'))  # Reset to black
    
    # Table header
    y = height - 240
    c.setFillColor(brand_blue)
    c.rect(72, y - 20, width - 144, 20, fill=True)
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(80, y - 15, "Item")
    c.drawString(250, y - 15, "Quantity")
    c.drawString(350, y - 15, "Unit Price")
    c.drawString(450, y - 15, "Amount")
    
    # Table content
    y -= 20
    c.setFillColor(HexColor('#000000'))
    c.setFont("Helvetica", 10)
    
    for idx, sale in enumerate(sales):
        y -= 20
        
        # Check if we need a new page
        if y < 100:
            c.showPage()
            c.setFont("Helvetica-Bold", 14)
            c.drawString(72, height - 50, f"Invoice {invoice.invoice_number} (Continued)")
            
            # Recreate table header
            y = height - 80
            c.setFillColor(brand_blue)
            c.rect(72, y - 20, width - 144, 20, fill=True)
            c.setFillColor(HexColor('#ffffff'))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(80, y - 15, "Item")
            c.drawString(250, y - 15, "Quantity")
            c.drawString(350, y - 15, "Unit Price")
            c.drawString(450, y - 15, "Amount")
            
            y -= 20
            c.setFillColor(HexColor('#000000'))
            c.setFont("Helvetica", 10)
        
        # Alternate row colors
        if idx % 2 == 0:
            c.setFillColor(HexColor('#f2f2f2'))
            c.rect(72, y - 15, width - 144, 20, fill=True)
            c.setFillColor(HexColor('#000000'))
            
        product_name = sale.product.product_name
        quantity_dozens = sale.quantity_sold // 12
        c.drawString(80, y, product_name)
        c.drawString(250, y, f"{quantity_dozens} dozens")
        c.drawString(350, y, f"₦{sale.unit_price:,.2f}")
        c.drawString(450, y, f"₦{sale.total_price:,.2f}")
    
    # Add discount information if applicable
    if discount:
        y -= 30
        c.setFont("Helvetica-Bold", 11)
        c.drawString(300, y, "Original Amount:")
        c.drawString(450, y, f"₦{discount.total_before_discount:,.2f}")
        
        y -= 20
        c.drawString(300, y, "Discount Applied:")
        c.drawString(450, y, f"₦{discount.discount_amount:,.2f}")
        
        # Add discount note
        y -= 10
        c.setFont("Helvetica-Italic", 9)
        c.drawString(300, y, "(Volume discount for qualified customer)")
    
    # Totals
    y -= 40
    c.setFont("Helvetica-Bold", 11)
    c.drawString(350, y, "Subtotal:")
    c.drawString(450, y, f"₦{invoice.total_amount:,.2f}")
    
    y -= 20
    c.drawString(350, y, "Amount Paid:")
    c.drawString(450, y, f"₦{invoice.amount_paid:,.2f}")
    
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y, "Balance Due:")
    c.drawString(450, y, f"₦{invoice.balance_due:,.2f}")
    
    # Add notes if any
    if invoice.notes:
        y -= 40
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, y, "Notes:")
        y -= 20
        c.setFont("Helvetica", 10)
        
        # Handle multi-line notes
        lines = wrap_text(invoice.notes, 80)
        for line in lines:
            c.drawString(72, y, line)
            y -= 15
    
    # Add footer
    c.setFont("Helvetica", 8)
    c.drawString(72, 50, "CONFIRM YOUR GOODS BEFORE LEAVING PREMISES.")
    c.drawString(72, 35, "WE WILL NOT BE LIABLE FOR ANY SHORTAGE THEREAFTER.")
    c.drawString(72, 20, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    c.save()
    
    return buffer

def wrap_text(text, width):
    """Wrap text to specified width"""
    if not text:
        return []
        
    words = text.split()
    lines = []
    line = []
    
    for word in words:
        if len(' '.join(line + [word])) <= width:
            line.append(word)
        else:
            lines.append(' '.join(line))
            line = [word]
    
    if line:
        lines.append(' '.join(line))
        
    return lines

def generate_receipt_pdf(payment):
    """Generate a PDF receipt for a payment"""
    buffer = BytesIO()
    
    # Set up the PDF
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Set brand blue color
    brand_blue = HexColor('#0066cc')
    
    # Add company header
    c.setFillColor(brand_blue)
    c.rect(0, height - 60, width, 60, fill=True)
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(72, height - 35, "DANGADO PLASTICS LTD.")
    
    # Add receipt title
    c.setFillColor(HexColor('#000000'))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 100, "PAYMENT RECEIPT")
    
    # Add receipt details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, height - 130, f"Receipt #: RCT-{payment.id}")
    c.drawString(72, height - 150, f"Date: {payment.payment_date.strftime('%Y-%m-%d')}")
    
    # Customer info
    c.drawString(72, height - 180, "Received From:")
    c.setFont("Helvetica", 12)
    c.drawString(180, height - 180, payment.invoice.customer.name)
    
    # Payment details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, height - 220, "Payment Details:")
    c.setFont("Helvetica", 12)
    c.drawString(72, height - 250, f"Invoice Number: {payment.invoice.invoice_number}")
    c.drawString(72, height - 270, f"Payment Method: {payment.payment_method}")
    c.drawString(72, height - 290, f"Amount Paid: ₦{payment.amount_paid:,.2f}")
    
    # Invoice status
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, height - 320, "Invoice Status:")
    c.setFont("Helvetica", 12)
    c.drawString(72, height - 340, f"Total Invoice Amount: ₦{payment.invoice.total_amount:,.2f}")
    c.drawString(72, height - 360, f"Total Amount Paid: ₦{payment.invoice.amount_paid:,.2f}")
    c.drawString(72, height - 380, f"Balance Due: ₦{payment.invoice.balance_due:,.2f}")
    c.drawString(72, height - 400, f"Status: {payment.invoice.payment_status.upper()}")
    
    # Thank you message
    c.setFont("Helvetica-Italic", 12)
    c.drawString(72, height - 440, "Thank you for your business!")
    
    # Add footer
    c.setFont("Helvetica", 8)
    c.drawString(72, 40, "DANGADO PLASTICS LTD.")
    c.drawString(72, 25, "No: 16B Sharada Industrial Phase III, Plot: 3 Kano.")
    c.drawString(400, 40, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    c.save()
    
    return buffer

def update_monthly_purchases(invoice_id):
    """Update monthly purchase records when a new invoice is created"""
    # Get invoice and its details
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return False
        
    # Get the year and month
    year = invoice.invoice_date.year
    month = invoice.invoice_date.month
    
    # Get all sales for this invoice
    sales = Sale.query.filter_by(invoice_id=invoice_id).all()
    
    # Group sales by category and update monthly purchases
    category_totals = {}
    
    for sale in sales:
        product = Product.query.get(sale.product_id)
        if not product:
            continue
            
        category = product.category
        if category not in category_totals:
            category_totals[category] = 0
            
        category_totals[category] += sale.total_price
    
    # Update or create monthly purchase records
    for category, total in category_totals.items():
        monthly_purchase = MonthlyPurchase.query.filter_by(
            customer_id=invoice.customer_id,
            year=year,
            month=month,
            category=category
        ).first()
        
        if monthly_purchase:
            monthly_purchase.total_amount += total
        else:
            monthly_purchase = MonthlyPurchase(
                customer_id=invoice.customer_id,
                year=year,
                month=month,
                category=category,
                total_amount=total
            )
            db.session.add(monthly_purchase)
    
    db.session.commit()
    return True


def generate_monthly_discounts(year=None, month=None):
    """Generate discount vouchers for eligible customers"""
    # Use current year and month if not specified
    if not year or not month:
        now = datetime.now()
        year = now.year
        month = now.month
    
    # Get all monthly purchases for the specified year and month
    monthly_purchases = MonthlyPurchase.query.filter_by(
        year=year,
        month=month
    ).all()
    
    vouchers_generated = 0
    
    for purchase in monthly_purchases:
        # Check if purchase amount exceeds the threshold (₦1,000,000)
        if purchase.total_amount >= 1000000:
            # Determine discount percentage based on category
            discount_percentage = 0.05 if purchase.category == 'Big' else 0.025
            
            # Calculate discount amount
            discount_amount = purchase.total_amount * discount_percentage
            
            # Generate a unique voucher number
            voucher_number = generate_voucher_number(year, month)
            
            # Create discount voucher
            voucher = DiscountVoucher(
                voucher_number=voucher_number,
                customer_id=purchase.customer_id,
                year=year,
                month=month,
                category=purchase.category,
                purchase_amount=purchase.total_amount,
                discount_percentage=discount_percentage * 100,  # Store as percentage (5.0 instead of 0.05)
                discount_amount=discount_amount,
                is_applied=False
            )
            
            db.session.add(voucher)
            vouchers_generated += 1
    
    db.session.commit()
    return vouchers_generated


def generate_voucher_number(year, month):
    """Generate a unique voucher number"""
    # Format: DV-YYYYMM-XXXXX
    prefix = f"DV-{year}{month:02d}-"
    random_suffix = ''.join(random.choices(string.digits, k=5))
    voucher_number = f"{prefix}{random_suffix}"
    
    # Check if voucher number already exists
    while DiscountVoucher.query.filter_by(voucher_number=voucher_number).first():
        random_suffix = ''.join(random.choices(string.digits, k=5))
        voucher_number = f"{prefix}{random_suffix}"
    
    return voucher_number


def apply_voucher_to_invoice(voucher_id, invoice_id):
    """Apply a discount voucher to an invoice"""
    voucher = DiscountVoucher.query.get(voucher_id)
    invoice = Invoice.query.get(invoice_id)
    
    if not voucher or not invoice:
        return False
    
    if voucher.is_applied:
        return False
    
    # Check if voucher belongs to the same customer
    if voucher.customer_id != invoice.customer_id:
        return False
    
    # Apply discount to invoice
    original_amount = invoice.total_amount
    invoice.total_amount -= voucher.discount_amount
    invoice.balance_due -= voucher.discount_amount
    
    # Update voucher status
    voucher.is_applied = True
    voucher.applied_at = datetime.now()
    voucher.applied_to_invoice_id = invoice.id
    
    db.session.commit()
    return True