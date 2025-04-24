import os
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from werkzeug.middleware.proxy_fix import ProxyFix

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "language_mirror_secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Simple in-memory storage for feedback
feedback_data = []

@app.route('/')
def index():
    """Redirects to admin feedback page"""
    return redirect(url_for('admin_feedback'))

@app.route('/admin/feedback', methods=['GET'])
def admin_feedback():
    """Admin page to view feedback"""
    # In a production environment, you would implement authentication here
    return render_template('admin_feedback.html', feedback=feedback_data)

@app.route('/api/feedback', methods=['GET'])
def get_feedback():
    """API endpoint to get feedback data"""
    return jsonify(feedback_data)

@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    """API endpoint to add feedback"""
    data = request.json
    if data and 'rating' in data:
        feedback_item = {
            'rating': data.get('rating'),
            'comment': data.get('comment', ''),
            'timestamp': datetime.now().isoformat(),
            'user_id': data.get('user_id', 'anonymous')
        }
        feedback_data.append(feedback_item)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Invalid feedback data'}), 400

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('base.html', 
                          content="Page not found. Please go to /admin/feedback"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logging.error(f"Server error: {str(e)}")
    return render_template('base.html', 
                          content="Internal server error. Please try again later."), 500

# Initialize the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
