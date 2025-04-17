from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Define helper functions at module level
def nl2br(value):
    if not value:
        return ""
    return value.replace('\n', '<br>')

def product(values):
    """Multiply values together"""
    result = 1
    for value in values:
        result *= value
    return result

def currency(value):
    if value is None:
        return "₦0.00"
    return f"₦{float(value):,.2f}"

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Add filters to jinja environment
    app.jinja_env.filters['nl2br'] = nl2br
    app.jinja_env.filters['currency'] = currency
    app.jinja_env.filters['product'] = product
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.auth import auth
    from app.routes.dashboard import dashboard
    from app.routes.customers import customers
    from app.routes.products import products
    from app.routes.invoices import invoices
    from app.routes.sales import sales
    from app.routes.payments import payments
    from app.routes.production import production
    from app.routes.reports import reports
    
    # Register the new blueprints (moved inside create_app function)
    from app.routes.discounts import discounts
    from app.routes.api import api
    
    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(customers)
    app.register_blueprint(products)
    app.register_blueprint(invoices)
    app.register_blueprint(sales)
    app.register_blueprint(payments)
    app.register_blueprint(production)
    app.register_blueprint(reports)
    app.register_blueprint(discounts)  # New blueprint
    app.register_blueprint(api)        # New blueprint
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Check if admin user exists, create if not
        from app.models import User
        if not User.query.filter_by(username='admin').first():
            from werkzeug.security import generate_password_hash
            admin = User(username='admin', 
                         email='admin@dangadoplastics.com',
                         password_hash=generate_password_hash('admin123'),
                         is_admin=True)
            db.session.add(admin)
            db.session.commit()
    
    # Setup scheduler (moved inside create_app)
    from app.scheduler import setup_scheduler
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        try:
            scheduler = setup_scheduler(app)
        except Exception as e:
            app.logger.error(f"Scheduler setup failed: {e}")
    
    return app