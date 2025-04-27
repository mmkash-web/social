# utils.py

import os
import logging
import shutil
from datetime import datetime
from flask import current_app
import yt_dlp
import uuid
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('socialsync.log')
    ]
)
logger = logging.getLogger('socialsync')

def create_download_dirs():
    """Create necessary download directories."""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        logger.info(f"Created download directory: {upload_folder}")

def validate_url(url):
    """Validate that URL is from a supported platform."""
    # Basic validation to check if URL is from a supported platform
    patterns = [
        r'(?:youtube\.com|youtu\.be)',
        r'(?:instagram\.com|instagr\.am)',
        r'(?:tiktok\.com)',
        r'(?:twitter\.com|x\.com)',
        r'(?:facebook\.com|fb\.com)'
    ]
    
    for pattern in patterns:
        if re.search(pattern, url):
            return True
    
    return False

def get_platform_from_url(url):
    """Determine the platform from the URL."""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'instagram.com' in url or 'instagr.am' in url:
        return 'instagram'
    elif 'tiktok.com' in url:
        return 'tiktok'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    elif 'facebook.com' in url or 'fb.com' in url:
        return 'facebook'
    else:
        return None

class DownloadManager:
    def __init__(self, config):
        """Initialize download manager with configuration."""
        self.download_path = config['UPLOAD_FOLDER']
        self.allowed_platforms = config['ALLOWED_PLATFORMS']
        
    def download_content(self, url, quality='high', content_type='any'):
        """Download content from social media platforms."""
        # Validate URL
        if not validate_url(url):
            return None, "URL is not from a supported platform"
            
        # Create a unique folder for this download
        unique_id = str(uuid.uuid4())
        download_dir = os.path.join(self.download_path, unique_id)
        os.makedirs(download_dir, exist_ok=True)
        
        # Get platform for specific handling
        platform = get_platform_from_url(url)
        logger.info(f"Downloading from {platform}: {url}")
        
        # Configure yt-dlp options based on quality and content type
        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'restrictfilenames': True,
            'noplaylist': True,
            'quiet': False,
            'no_warnings': False,
        }
        
        # Quality settings
        if quality == 'low':
            if content_type == 'video':
                ydl_opts['format'] = 'worst[ext=mp4]'
            elif content_type == 'audio':
                ydl_opts['format'] = 'worstaudio[ext=m4a]'
            elif content_type == 'image':
                ydl_opts['format'] = 'thumbnailsonly'
        elif quality == 'medium':
            if content_type == 'video':
                ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]'
            elif content_type == 'audio':
                ydl_opts['format'] = 'bestaudio[abr<=128][ext=m4a]'
        else:  # high quality (default)
            if content_type == 'video':
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
            elif content_type == 'audio':
                ydl_opts['format'] = 'bestaudio[ext=m4a]'
                
        # Platform-specific options
        if platform == 'instagram':
            ydl_opts['cookiefile'] = 'instagram_cookies.txt'
        elif platform == 'facebook':
            ydl_opts['cookiefile'] = 'facebook_cookies.txt'
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_files = os.listdir(download_dir)
                
                if not downloaded_files:
                    logger.error(f"No files downloaded for {url}")
                    return None, "No files were downloaded"
                
                # Get the path of the downloaded file
                file_path = os.path.join(download_dir, downloaded_files[0])
                logger.info(f"Successfully downloaded: {file_path}")
                return file_path, None
        except Exception as e:
            logger.error(f"Download error for {url}: {str(e)}")
            return None, str(e)
            
    def cleanup_old_files(self, max_age_seconds):
        """Remove old download directories."""
        try:
            cutoff_time = datetime.now().timestamp() - max_age_seconds
            deleted_count = 0
            
            for folder in os.listdir(self.download_path):
                folder_path = os.path.join(self.download_path, folder)
                if os.path.isdir(folder_path):
                    folder_time = os.path.getctime(folder_path)
                    if folder_time < cutoff_time:
                        shutil.rmtree(folder_path)
                        deleted_count += 1
                        
            logger.info(f"Cleaned up {deleted_count} old download directories")
            return deleted_count
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return 0

# app_extended.py

from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from config import get_config
from utils import create_download_dirs, DownloadManager
import logging

# Initialize logging
logger = logging.getLogger('socialsync')

def create_app(config_name='default'):
    """Application factory function."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(get_config())
    
    # Create download directories
    create_download_dirs()
    
    # Setup rate limiting
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=app.config['RATELIMIT_STORAGE_URL']
    )
    
    # Initialize download manager
    download_manager = DownloadManager(app.config)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/download', methods=['POST'])
    @limiter.limit("5 per minute")
    def download():
        if request.method == 'POST':
            url = request.form.get('url')
            quality = request.form.get('quality', 'high')
            content_type = request.form.get('content_type', 'any')
            
            if not url:
                return jsonify({'status': 'error', 'message': 'URL is required'})
            
            logger.info(f"Download request: URL={url}, Quality={quality}, Type={content_type}")
            
            try:
                file_path, error = download_manager.download_content(url, quality, content_type)
                
                if error:
                    logger.warning(f"Download failed: {error}")
                    return jsonify({'status': 'error', 'message': error})
                
                if file_path:
                    # Get just the filename without the path
                    filename = os.path.basename(file_path)
                    download_url = url_for('serve_file', file_path=file_path, filename=filename)
                    
                    logger.info(f"Download success, ready to serve: {filename}")
                    return jsonify({
                        'status': 'success', 
                        'message': 'Download completed!',
                        'download_url': download_url
                    })
                else:
                    return jsonify({'status': 'error', 'message': 'Failed to download the file'})
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return jsonify({'status': 'error', 'message': str(e)})
    
    @app.route('/serve/<path:file_path>/<filename>')
    def serve_file(file_path, filename):
        """Serve the downloaded file to the user."""
        return send_file(file_path, as_attachment=True, download_name=filename)
    
    @app.route('/supported-platforms')
    def supported_platforms():
        """Return a list of supported platforms."""
        return jsonify(app.config['ALLOWED_PLATFORMS'])
    
    @app.route('/health')
    def health_check():
        """Simple health check endpoint."""
        return jsonify({'status': 'healthy'})
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handle rate limit exceeded errors."""
        return jsonify({'status': 'error', 'message': 'Rate limit exceeded. Please try again later.'}), 429
    
    # Schedule cleanup of old files
    @app.before_request
    def cleanup_old_files():
        try:
            # Get retention period from config
            retention_period = app.config['FILE_RETENTION_PERIOD'].total_seconds()
            download_manager.cleanup_old_files(retention_period)
        except Exception:
            # Ignore cleanup errors to not affect user experience
            pass
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=app.config['DEBUG'], host='0.0.0.0')