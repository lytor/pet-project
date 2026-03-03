from flask import Flask, jsonify, request
import psycopg2
import redis
import os
import socket
import datetime
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# Чтение секретов из файлов
def read_secret(path):
    with open(path, 'r') as f:
        return f.read().strip()

# Подключение к PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'myapp'),
        user=os.getenv('POSTGRES_USER', 'user'),
        password=read_secret('/run/secrets/db_password')
    )

# Подключение к Redis
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=os.getenv('REDIS_PORT', 6379),
    password=read_secret('/run/secrets/redis_password'),
    decode_responses=True
)

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/api/info')
def info():
    return jsonify({
        'host': socket.gethostname(),
        'version': '1.0.0',
        'services': {
            'postgres': check_postgres(),
            'redis': check_redis()
        }
    })

@app.route('/api/data', methods=['GET', 'POST'])
def data():
    if request.method == 'POST':
        # Сохраняем в базу и кэшируем
        data = request.json
        # TODO: сохранение в PostgreSQL
        redis_client.setex(f"data:{data.get('id')}", 3600, str(data))
        return jsonify({'status': 'saved'})
    else:
        # Сначала проверяем кэш
        cached = redis_client.get('data:list')
        if cached:
            return jsonify({'source': 'cache', 'data': eval(cached)})
        
        # TODO: чтение из PostgreSQL
        result = {'example': 'data'}
        redis_client.setex('data:list', 60, str(result))
        return jsonify({'source': 'database', 'data': result})

def check_postgres():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        return 'connected'
    except Exception as e:
        return f'error: {str(e)}'

def check_redis():
    try:
        return 'connected' if redis_client.ping() else 'disconnected'
    except Exception as e:
        return f'error: {str(e)}'

@app.route('/health')
def health_check():
    health_status = {
        'status': 'healthy',
        'components': {
            'database': check_postgres(),
            'redis': check_redis(),
            'app': 'running'
        }
    }
    return health_status, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
