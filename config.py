# config.py

import os
from datetime import timedelta

class Config:
    """Base configuration class."""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-for-development')
    
    # Download settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'downloads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB limit for uploads
    ALLOWED_PLATFORMS = ['youtube', 'instagram', 'tiktok', 'twitter', 'facebook']
    
    # File cleanup settings
    FILE_RETENTION_PERIOD = timedelta(hours=24)
    
    # Rate limiting
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for production configuration")
        
    # Production-specific settings
    PREFERRED_URL_SCHEME = 'https'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    
    # Use an in-memory file system for testing
    UPLOAD_FOLDER = '/tmp/test_uploads'
    
    # Shorter retention for tests
    FILE_RETENTION_PERIOD = timedelta(minutes=5)


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Return the appropriate configuration object based on environment variable."""
    config_name = os.environ.get('FLASK_CONFIG', 'default')
    return config[config_name]