import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dangado-plastics-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///dangado.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # For production, use PostgreSQL
    # SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost/dangado'
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    
    # Company info
    COMPANY_NAME = "DANGADO PLASTICS LTD. RC 1264944"
    COMPANY_ADDRESS = "No: 16B Sharada Industrial Phase III, Plot: 3 Kano."