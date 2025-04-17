# app/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.utils import generate_monthly_discounts
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def setup_scheduler(app):
    """Set up scheduled tasks for the application"""
    with app.app_context():
        scheduler = BackgroundScheduler()
        
        # Schedule monthly discount generation
        # Run on the 1st day of each month at 00:01 AM
        scheduler.add_job(
            process_monthly_discounts,
            trigger=CronTrigger(day='1', hour='0', minute='1'),
            id='generate_monthly_discounts',
            name='Generate monthly discount vouchers',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Scheduler started, monthly discount generation scheduled.")
        
        return scheduler

def process_monthly_discounts():
    """Process monthly discount generation for the previous month"""
    now = datetime.now()
    
    # Calculate previous month
    year = now.year
    month = now.month - 1
    
    if month == 0:  # If it's January, go back to December of previous year
        month = 12
        year -= 1
    
    logger.info(f"Generating monthly discounts for {month}/{year}")
    vouchers_count = generate_monthly_discounts(year, month)
    logger.info(f"Generated {vouchers_count} discount vouchers for {month}/{year}")