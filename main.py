from flask import Flask, jsonify, render_template, request, redirect, url_for, abort
import logging
import os
import threading
import time
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Store feedback data in memory
feedback_data = []

# Start bot in separate thread
def start_bot_thread():
    try:
        # Import runs in thread to avoid blocking web server
        from language_mirror_telebot import main as run_bot
        logger.info("Starting bot in background thread...")
        run_bot()
    except Exception as e:
        logger.error(f"Error starting bot thread: {e}")

# Start bot in background if TELEGRAM_TOKEN is set
if os.environ.get("TELEGRAM_TOKEN"):
    bot_thread = threading.Thread(target=start_bot_thread)
    bot_thread.daemon = True  # Set as daemon so it exits when main thread exits
    bot_thread.start()
    logger.info("Bot thread started")
else:
    logger.warning("TELEGRAM_TOKEN not set. Bot will not start.")

@app.route('/')
def index():
    """Redirects to admin feedback page"""
    return redirect(url_for('admin_feedback'))

@app.route('/admin/feedback')
def admin_feedback():
    """Admin page to view feedback"""
    return render_template('admin_feedback.html')

@app.route('/api/feedback', methods=['GET'])
def get_feedback():
    """API endpoint to get feedback data"""
    return jsonify(feedback_data)

@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    """API endpoint to add feedback"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    feedback_item = {
        "id": len(feedback_data) + 1,
        "user_id": data.get("user_id", "unknown"),
        "username": data.get("username", "unknown"),
        "rating": data.get("rating", "unknown"),
        "comment": data.get("comment", ""),
        "timestamp": datetime.now().isoformat()
    }
    
    feedback_data.append(feedback_item)
    return jsonify({"success": True, "id": feedback_item["id"]}), 201

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Page not found"}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({"error": "Server error"}), 500

# Create templates directory if it doesn't exist
os.makedirs('templates', exist_ok=True)

# Create admin_feedback.html template if it doesn't exist
template_path = 'templates/admin_feedback.html'
if not os.path.exists(template_path):
    with open(template_path, 'w') as f:
        f.write("""<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Language Mirror - Feedback Dashboard</title>
    <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
</head>
<body>
    <div class="container mt-4">
        <h1 class="mb-4">Language Mirror Bot - Feedback Dashboard</h1>
        
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h5>User Feedback</h5>
                    </div>
                    <div class="card-body">
                        <div id="feedback-content">
                            <p class="text-center">Loading feedback data...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-4">
            <p class="text-muted">
                <strong>Status:</strong> <span id="bot-status">Checking...</span>
            </p>
        </div>
    </div>
    
    <script>
        // Function to load feedback data
        function loadFeedback() {
            fetch('/api/feedback')
                .then(response => response.json())
                .then(data => {
                    const feedbackDiv = document.getElementById('feedback-content');
                    
                    if (data.length === 0) {
                        feedbackDiv.innerHTML = '<p class="text-center">No feedback data available yet.</p>';
                        return;
                    }
                    
                    let tableHtml = `
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>User</th>
                                        <th>Rating</th>
                                        <th>Comment</th>
                                        <th>Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    data.forEach(item => {
                        // Format the timestamp
                        let timestamp = new Date(item.timestamp);
                        let formattedTime = timestamp.toLocaleString();
                        
                        // Create rating display with emojis
                        let ratingDisplay = item.rating;
                        if (item.rating === 'helpful') {
                            ratingDisplay = '👍 Helpful';
                        } else if (item.rating === 'okay') {
                            ratingDisplay = '🤔 Okay';
                        } else if (item.rating === 'not_helpful') {
                            ratingDisplay = '👎 Not helpful';
                        }
                        
                        tableHtml += `
                            <tr>
                                <td>${item.id}</td>
                                <td>${item.username} (${item.user_id})</td>
                                <td>${ratingDisplay}</td>
                                <td>${item.comment || '-'}</td>
                                <td>${formattedTime}</td>
                            </tr>
                        `;
                    });
                    
                    tableHtml += `
                                </tbody>
                            </table>
                        </div>
                    `;
                    
                    feedbackDiv.innerHTML = tableHtml;
                })
                .catch(error => {
                    console.error('Error loading feedback:', error);
                    document.getElementById('feedback-content').innerHTML = 
                        '<div class="alert alert-danger">Error loading feedback data.</div>';
                });
        }
        
        // Check bot status
        function checkBotStatus() {
            // This is a simple check - in a real app, you'd have an API endpoint to check status
            const botStatusSpan = document.getElementById('bot-status');
            
            fetch('/api/feedback')
                .then(response => {
                    if (response.ok) {
                        botStatusSpan.innerHTML = '<span class="text-success">Server is running</span>';
                    } else {
                        botStatusSpan.innerHTML = '<span class="text-danger">Server error</span>';
                    }
                })
                .catch(() => {
                    botStatusSpan.innerHTML = '<span class="text-danger">Server unreachable</span>';
                });
        }
        
        // Load data when page loads
        document.addEventListener('DOMContentLoaded', () => {
            loadFeedback();
            checkBotStatus();
            
            // Refresh data every 30 seconds
            setInterval(loadFeedback, 30000);
        });
    </script>
</body>
</html>
""")

# Create static directory if it doesn't exist
os.makedirs('static', exist_ok=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
