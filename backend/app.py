from flask import Flask, jsonify, request
import psycopg2
from psycopg2 import pool
import redis
import os
import socket
import datetime
import logging
import time
from functools import wraps
from prometheus_flask_exporter import PrometheusMetrics
from werkzeug.middleware.proxy_fix import ProxyFix

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
metrics = PrometheusMetrics(app)

# Статическая информация как метка для всех метрик
metrics.info('app_info', 'Application info', version='1.0.0')

# Чтение секретов из файлов с обработкой ошибок
def read_secret(path, default=None):
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Secret file not found: {path}")
        return default
    except Exception as e:
        logger.error(f"Error reading secret {path}: {e}")
        return default

# Пул подключений к PostgreSQL для производительности
try:
    postgres_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        host=os.getenv('DB_HOST', 'postgres'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'myapp'),
        user=os.getenv('POSTGRES_USER', 'user'),
        password=read_secret('/run/secrets/db_password', 'postgres')
    )
    logger.info("PostgreSQL connection pool created")
except Exception as e:
    logger.error(f"Failed to create PostgreSQL pool: {e}")
    postgres_pool = None

# Подключение к Redis
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=read_secret('/run/secrets/redis_password'),
        decode_responses=True,
        socket_connect_timeout=2,
        retry_on_timeout=True
    )
    redis_client.ping()  # Проверка подключения
    logger.info("Redis connected successfully")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

# Декоратор для логирования времени выполнения
def log_execution_time(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start = time.time()
        response = f(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{f.__name__} executed in {duration:.3f}s")
        return response
    return decorated_function

# Middleware для логирования запросов
@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response_info(response):
    logger.info(f"Response: {response.status_code}")
    return response

# Эндпоинты
@app.route('/api/health')
@log_execution_time
def health():
    """Базовый health check для Kubernetes/Docker"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'host': socket.gethostname()
    })

@app.route('/api/info')
@log_execution_time
def info():
    """Информация о сервисе и его зависимостях"""
    return jsonify({
        'host': socket.gethostname(),
        'version': '1.0.0',
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'services': {
            'postgres': check_postgres(),
            'redis': check_redis()
        },
        'uptime': get_uptime()
    })

@app.route('/api/data', methods=['GET', 'POST'])
@log_execution_time
def data():
    """Работа с данными с кэшированием"""
    try:
        if request.method == 'POST':
            return handle_post_data()
        else:
            return handle_get_data()
    except Exception as e:
        logger.error(f"Error in /api/data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def handle_post_data():
    """Обработка POST запроса"""
    data = request.json
    if not data or 'id' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    
    # TODO: сохранение в PostgreSQL
    # with postgres_pool.getconn() as conn:
    #     cur = conn.cursor()
    #     cur.execute(...)
    
    # Кэшируем в Redis
    if redis_client:
        redis_client.setex(
            f"data:{data['id']}", 
            3600, 
            str(data)
        )
    
    logger.info(f"Data saved: {data['id']}")
    return jsonify({'status': 'saved', 'id': data['id']}), 201

def handle_get_data():
    """Обработка GET запроса с кэшированием"""
    # Сначала проверяем кэш
    if redis_client:
        cached = redis_client.get('data:list')
        if cached:
            logger.info("Returning cached data")
            return jsonify({'source': 'cache', 'data': eval(cached)})
    
    # TODO: чтение из PostgreSQL
    # with postgres_pool.getconn() as conn:
    #     cur = conn.cursor()
    #     cur.execute(...)
    
    result = {'example': 'data', 'timestamp': time.time()}
    
    # Кэшируем результат
    if redis_client:
        redis_client.setex('data:list', 60, str(result))
    
    logger.info("Returning fresh data from database")
    return jsonify({'source': 'database', 'data': result})

def check_postgres():
    """Проверка подключения к PostgreSQL"""
    if not postgres_pool:
        return 'not configured'
    try:
        conn = postgres_pool.getconn()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        postgres_pool.putconn(conn)
        return 'connected'
    except Exception as e:
        logger.error(f"PostgreSQL check failed: {e}")
        return f'error: {str(e)}'

def check_redis():
    """Проверка подключения к Redis"""
    if not redis_client:
        return 'not configured'
    try:
        return 'connected' if redis_client.ping() else 'disconnected'
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        return f'error: {str(e)}'

def get_uptime():
    """Получение времени работы (можно реализовать по-разному)"""
    if hasattr(app, 'start_time'):
        return str(datetime.timedelta(seconds=time.time() - app.start_time))
    return 'unknown'

# Совместимость со старым endpoint
@app.route('/health')
def health_check():
    """Старый endpoint для обратной совместимости"""
    return jsonify({
        'status': 'healthy',
        'components': {
            'database': check_postgres(),
            'redis': check_redis(),
            'app': 'running'
        }
    }), 200

# Обработчик 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

# Обработчик 500
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.start_time = time.time()
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)