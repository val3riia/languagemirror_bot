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

# Import models
from models import db, User, Session, Message, Feedback

# Create Flask app
app = Flask(__name__, static_url_path='/static', static_folder='static')

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Маскируем пароль для логов (например postgresql://user:pass@host:port/dbname)
    masked_url = database_url
    if "@" in database_url:
        parts = database_url.split("@")
        user_pass = parts[0].split("://")[1]
        if ":" in user_pass:
            # Заменяем пароль на ***
            user = user_pass.split(":")[0]
            masked_url = database_url.replace(user_pass, f"{user}:***")
        
    logger.info(f"Используется база данных: {masked_url}")
    
    # Fix potential postgres:// vs postgresql:// URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        logger.info("URL базы данных преобразован из postgres:// в postgresql://")
        
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    # Конфигурация с обязательным SSL для Render.com PostgreSQL
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        # Render.com требует SSL/TLS
        "connect_args": {
            "sslmode": "require",
            "application_name": "Language Mirror Bot",
        }
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Добавляем детальное логирование SQL-запросов при отладке
    app.config["SQLALCHEMY_ECHO"] = os.environ.get("DEBUG", "False").lower() in ["true", "1", "yes"]
    
    # Initialize database with app
    db.init_app(app)
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            logger.error("Check your DATABASE_URL. Правильный формат: postgresql://username:password@hostname:port/database_name")
            # Проверка основных атрибутов подключения
            try:
                import sqlalchemy
                engine = sqlalchemy.create_engine(
                    database_url,
                    connect_args={"sslmode": "require"}
                )
                connection = engine.connect()
                connection.close()
                logger.info("Проверка подключения к базе данных прошла успешно!")
            except Exception as conn_error:
                logger.error(f"Не удалось подключиться к базе данных: {str(conn_error)}")
                logger.error("Проверьте также, что ваша база данных доступна из интернета и не заблокирована файрволом.")
                # Попробуем проверить внутренний URL
                if "internal" not in database_url and "private" not in database_url:
                    logger.warning("Возможно, вы используете внешний URL базы данных. В Render.com лучше использовать внутренний URL (Internal Database URL).")
else:
    logger.error("DATABASE_URL environment variable not set. Bot будет работать с ограниченной функциональностью.")

# Temporary storage for feedback data (for backward compatibility)
feedback_data = []

# Start bot in separate thread
def start_bot_thread():
    try:
        # Wait a bit to ensure Flask app is fully initialized
        time.sleep(2)
        
        # Сначала решаем проблему конфликтов ботов
        try:
            logger.info("Removing Telegram webhook to prevent conflicts...")
            # Получение токена
            token = os.environ.get("TELEGRAM_TOKEN")
            if token:
                # Делаем запрос к API Telegram для удаления webhook
                import requests
                response = requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
                if response.status_code == 200 and response.json().get("ok", False):
                    logger.info("Webhook successfully removed")
                else:
                    logger.warning(f"Failed to remove webhook: {response.text}")
            else:
                logger.warning("No TELEGRAM_TOKEN found, can't remove webhook")
            
            # Ждем немного после удаления webhook
            time.sleep(1)
        except Exception as webhook_error:
            logger.error(f"Error removing webhook: {webhook_error}")
        
        # Import runs in thread to avoid blocking web server
        from language_mirror_telebot import main as run_bot, bot
        
        # Еще раз удаляем webhook через объект бота
        try:
            bot.remove_webhook()
            logger.info("Webhook removed through bot.remove_webhook()")
            time.sleep(1)
        except Exception as bot_webhook_error:
            logger.error(f"Error removing webhook via bot: {bot_webhook_error}")
        
        # Запускаем бота
        logger.info("Starting bot in background thread...")
        run_bot()
    except Exception as e:
        logger.error(f"Error starting bot thread: {e}")
        # Uncomment for debug
        # import traceback
        # logger.error(traceback.format_exc())

# Проверяем наличие переменной окружения BOT_AUTO_START
bot_auto_start_value = os.environ.get("BOT_AUTO_START", "False").strip().lower()
# Принимаем различные варианты "истинных" значений
bot_auto_start = bot_auto_start_value in ["true", "yes", "1", "on", "t", "y"]
logger.info(f"BOT_AUTO_START={bot_auto_start_value} (интерпретировано как {bot_auto_start})")

has_telegram_token = bool(os.environ.get("TELEGRAM_TOKEN"))
database_configured = bool(database_url)

# Временно принудительно активируем автозапуск для отладки
forced_auto_start = True

if (bot_auto_start or forced_auto_start) and has_telegram_token:
    # Запускаем бота в отдельном потоке, флаг BOT_AUTO_START или форсирован, и есть токен
    bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
    bot_thread.start()
    
    if forced_auto_start and not bot_auto_start:
        logger.info("Bot thread started due to forced_auto_start=True (for debugging)")
    else:
        logger.info("Bot thread started successfully (automatic start enabled)")
    
    if not database_configured:
        logger.warning("Database not configured properly. Bot will work with limited functionality.")
else:
    if not bot_auto_start and not forced_auto_start:
        logger.info("Automatic bot startup disabled. Set BOT_AUTO_START=True to enable.")
    if not has_telegram_token:
        logger.warning("TELEGRAM_TOKEN environment variable is not set. Bot cannot start.")

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
    # Если база данных не настроена, используем данные из памяти
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        return jsonify(feedback_data)
    
    try:
        # Получаем данные из базы данных
        feedback_items = Feedback.query.order_by(Feedback.timestamp.desc()).all()
        result = []
        
        for item in feedback_items:
            # Находим пользователя
            user = User.query.get(item.user_id)
            username = user.username if user else "unknown"
            
            result.append({
                "id": item.id,
                "user_id": user.telegram_id if user else "unknown",
                "username": username,
                "rating": item.rating,
                "comment": item.comment or "",
                "timestamp": item.timestamp.isoformat()
            })
        
        return jsonify(result)
    except Exception:
        logger.error("Error getting feedback. Check your database connection.")
        # В случае ошибки базы данных, возвращаем данные из памяти
        return jsonify(feedback_data)

@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    """API endpoint to add feedback"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # Если база данных настроена, сохраняем в неё
        if app.config.get("SQLALCHEMY_DATABASE_URI"):
            # Пробуем найти пользователя по telegram_id
            telegram_id = int(data.get("user_id", 0))
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            # Если пользователь не найден, создаем его
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=data.get("username", "unknown")
                )
                db.session.add(user)
                db.session.commit()
            
            # Создаем запись обратной связи
            feedback = Feedback(
                user_id=user.id,
                rating=data.get("rating", "unknown"),
                comment=data.get("comment", "")
            )
            
            db.session.add(feedback)
            db.session.commit()
            
            return jsonify({"success": True, "id": feedback.id}), 201
        
        # Если база данных не настроена, сохраняем в памяти
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
        
    except Exception:
        logger.error("Error adding feedback. Check your database connection.")
        return jsonify({"error": "Database error occurred while adding feedback"}), 500

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
