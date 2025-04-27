# SocialSync Downloader - A Professional Social Media Content Downloader
# app.py

from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import os
import yt_dlp
import uuid
import shutil
from datetime import datetime

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'downloads'
ALLOWED_PLATFORMS = ['youtube', 'instagram', 'tiktok', 'twitter', 'facebook']
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class SocialMediaDownloader:
    def __init__(self):
        self.download_path = UPLOAD_FOLDER
        
    def download_content(self, url, quality='high', content_type='any'):
        """Download content from social media platforms"""
        # Create a unique folder for this download
        unique_id = str(uuid.uuid4())
        download_dir = os.path.join(self.download_path, unique_id)
        os.makedirs(download_dir, exist_ok=True)
        
        # Configure yt-dlp options based on quality and content type
        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'restrictfilenames': True,
            'noplaylist': True,
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
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_files = os.listdir(download_dir)
                
                if not downloaded_files:
                    return None, "No files were downloaded"
                
                # Get the path of the downloaded file
                file_path = os.path.join(download_dir, downloaded_files[0])
                return file_path, None
        except Exception as e:
            return None, str(e)

downloader = SocialMediaDownloader()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    if request.method == 'POST':
        url = request.form.get('url')
        quality = request.form.get('quality', 'high')
        content_type = request.form.get('content_type', 'any')
        
        if not url:
            return jsonify({'status': 'error', 'message': 'URL is required'})
        
        try:
            file_path, error = downloader.download_content(url, quality, content_type)
            
            if error:
                return jsonify({'status': 'error', 'message': error})
            
            if file_path:
                # Get just the filename without the path
                filename = os.path.basename(file_path)
                download_url = url_for('serve_file', file_path=file_path, filename=filename)
                return jsonify({
                    'status': 'success', 
                    'message': 'Download completed!',
                    'download_url': download_url
                })
            else:
                return jsonify({'status': 'error', 'message': 'Failed to download the file'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})

@app.route('/serve/<path:file_path>/<filename>')
def serve_file(file_path, filename):
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/supported-platforms')
def supported_platforms():
    return jsonify(ALLOWED_PLATFORMS)

# Clean up old downloads periodically
@app.before_request
def cleanup_old_files():
    try:
        cutoff_time = datetime.now().timestamp() - (24 * 60 * 60)  # 24 hours
        for folder in os.listdir(UPLOAD_FOLDER):
            folder_path = os.path.join(UPLOAD_FOLDER, folder)
            if os.path.isdir(folder_path):
                folder_time = os.path.getctime(folder_path)
                if folder_time < cutoff_time:
                    shutil.rmtree(folder_path)
    except Exception:
        pass  # Ignore cleanup errors

if __name__ == '__main__':
    app.run(debug=True)