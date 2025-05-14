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
# Используем URL базы данных из переменных окружения
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
    # Конфигурация для PostgreSQL с минимальными настройками
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        # Настройки для Render.com PostgreSQL
        "connect_args": {
            "sslmode": "require",  # Render.com требует SSL
            "connect_timeout": 30,  # Увеличиваем таймаут подключения
            "keepalives": 1,        # Держим соединение активным
            "keepalives_idle": 30,  # Проверка активности каждые 30 секунд
            "keepalives_interval": 10  # Интервал повторной проверки 10 секунд
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
                    connect_args={
                        "sslmode": "require",
                        "connect_timeout": 30
                    }
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

# Переменные для хранения менеджера Google Sheets и данных обратной связи
sheets_manager = None
feedback_data = []

# Инициализация Google Sheets
def init_google_sheets():
    """Инициализация Google Sheets для хранения данных."""
    global sheets_manager
    
    try:
        # Проверяем наличие переменных окружения для Google Sheets
        google_creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
        google_sheets_key = os.environ.get("GOOGLE_SHEETS_KEY")
        use_google_sheets = os.environ.get("USE_GOOGLE_SHEETS", "True").lower() == "true"
        
        if use_google_sheets and google_creds_path and google_sheets_key:
            from sheets_manager import SheetsManager
            
            logger.info("Initializing Google Sheets for data storage")
            sheets_manager = SheetsManager(
                credentials_path=google_creds_path,
                spreadsheet_key=google_sheets_key
            )
            
            if sheets_manager and sheets_manager.sheet:
                logger.info("Google Sheets initialized successfully")
                return True
            else:
                logger.warning("Google Sheets not fully initialized, falling back to memory storage")
                return False
        else:
            if not use_google_sheets:
                logger.info("Google Sheets disabled in configuration, using memory storage")
            else:
                logger.warning("Google Sheets configuration missing, falling back to memory storage")
            return False
            
    except ImportError:
        logger.warning("Google Sheets packages not installed, falling back to memory storage")
        return False
    except Exception as e:
        logger.error(f"Error initializing Google Sheets: {e}")
        return False

# Попытка инициализации Google Sheets
google_sheets_available = init_google_sheets()

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
    global sheets_manager
    
    # Сначала пробуем получить данные из Google Sheets
    if google_sheets_available and sheets_manager:
        try:
            # Получаем данные обратной связи из Google Sheets
            google_sheets_data = sheets_manager.get_all_feedback()
            
            # Преобразуем данные в нужный формат
            result = []
            for item in google_sheets_data:
                # Получаем необходимые данные и устанавливаем значения по умолчанию
                telegram_id = item.get('telegram_id', '')
                username = item.get('username', 'unknown')
                rating = item.get('rating', 'unknown')
                comment = item.get('comment', '')
                
                # Форматируем timestamp
                timestamp = item.get('created_at', '')
                if not timestamp:
                    timestamp = datetime.now().isoformat()
                
                # Проверяем, есть ли id (может отсутствовать в Google Sheets)
                item_id = item.get('id', None)
                if item_id is None:
                    # Если id нет, генерируем его на основе индекса
                    item_id = len(result) + 1
                
                result.append({
                    "id": item_id,
                    "user_id": telegram_id,
                    "username": username,
                    "rating": rating,
                    "comment": comment,
                    "timestamp": timestamp
                })
            
            # Сортируем результаты по времени (новые сначала)
            result.sort(key=lambda x: x["timestamp"], reverse=True)
            logger.info(f"Successfully retrieved {len(result)} feedback items from Google Sheets")
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"Error getting feedback from Google Sheets: {e}")
            # В случае ошибки переходим к следующему методу
    
    # Затем пробуем получить данные из базы данных PostgreSQL
    if app.config.get("SQLALCHEMY_DATABASE_URI"):
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
            
            logger.info(f"Successfully retrieved {len(result)} feedback items from PostgreSQL")
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error getting feedback from PostgreSQL: {e}")
            # В случае ошибки базы данных, переходим к следующему методу
    
    # Если другие методы не сработали, возвращаем данные из памяти
    logger.warning("Using in-memory feedback data as fallback")
    return jsonify(feedback_data)

@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    """API endpoint to add feedback"""
    global sheets_manager
    
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # Сначала пробуем сохранить в Google Sheets
        if google_sheets_available and sheets_manager:
            try:
                # Извлекаем данные из запроса
                telegram_id = data.get("user_id", 0)
                username = data.get("username", "unknown")
                first_name = data.get("first_name", "")
                last_name = data.get("last_name", "")
                rating = data.get("rating", "unknown")
                comment = data.get("comment", "")
                session_id = data.get("session_id")
                
                # Добавляем отзыв в Google Sheets
                sheets_manager.add_feedback(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    session_id=session_id,
                    rating=rating,
                    comment=comment
                )
                
                logger.info(f"Feedback successfully added to Google Sheets. User: {username}, Rating: {rating}")
                
                # Получаем ID записи (хотя в Google Sheets это не так важно)
                # В Google Sheets ID формируется автоматически
                return jsonify({"success": True, "source": "google_sheets"}), 201
                
            except Exception as e:
                logger.error(f"Error adding feedback to Google Sheets: {e}")
                # В случае ошибки переходим к следующему методу
        
        # Затем пробуем сохранить в PostgreSQL
        if app.config.get("SQLALCHEMY_DATABASE_URI"):
            try:
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
                
                logger.info(f"Feedback successfully added to PostgreSQL. User: {user.username}, Rating: {feedback.rating}")
                return jsonify({"success": True, "id": feedback.id, "source": "postgresql"}), 201
                
            except Exception as e:
                logger.error(f"Error adding feedback to PostgreSQL: {e}")
                # В случае ошибки переходим к следующему методу
        
        # Если другие методы не сработали, сохраняем в памяти
        feedback_item = {
            "id": len(feedback_data) + 1,
            "user_id": data.get("user_id", "unknown"),
            "username": data.get("username", "unknown"),
            "rating": data.get("rating", "unknown"),
            "comment": data.get("comment", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        feedback_data.append(feedback_item)
        logger.info(f"Feedback added to memory storage. Total items: {len(feedback_data)}")
        return jsonify({"success": True, "id": feedback_item["id"], "source": "memory"}), 201
        
    except Exception as e:
        logger.error(f"Error adding feedback: {e}")
        return jsonify({"error": "Error occurred while adding feedback"}), 500

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
