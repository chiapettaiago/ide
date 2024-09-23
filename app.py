from flask import Flask, request, render_template, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import os
import re
import platform
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a secure random key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

USERS_DIR = 'users'
if not os.path.exists(USERS_DIR):
    os.makedirs(USERS_DIR)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# Define a lista de comandos ou módulos perigosos
FORBIDDEN_PATTERNS = [
    r'import\s+os',          # Impedir importação do módulo 'os'
    r'import\s+subprocess',  # Impedir importação do módulo 'subprocess'
    r'eval\(',               # Impedir uso de eval
    r'exec\(',               # Impedir uso de exec
    r'system\(',             # Impedir uso de system para executar comandos shell
    r'open\(',               # Impedir o uso de open (potencialmente perigoso)
    r'rm\s+-rf',             # Evitar comandos de remoção
    r'import\s+sys',         # Evitar importação do sys (pode manipular saída de dados)
]

# Função para verificar padrões perigosos no código
def contains_forbidden_patterns(code):
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return True
    return False

# Decorator para requerer login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['username'] = username
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
        else:
            new_user = User(username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            os.makedirs(os.path.join(USERS_DIR, username), exist_ok=True)
            flash('Registered successfully. Please log in.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/files', methods=['GET'])
@login_required
def list_files():
    username = session['username']
    path = request.args.get('path', '')
    full_path = os.path.join(USERS_DIR, username, path)
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'Path does not exist'}), 400

    files = [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]
    folders = [f for f in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, f))]
    
    return jsonify({'files': files, 'folders': folders})

@app.route('/load/<path:filename>', methods=['GET'])
@login_required
def load_file(filename):
    username = session['username']
    full_path = os.path.join(USERS_DIR, username, filename)
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            return f.read()
    return '', 404

@app.route('/save', methods=['POST'])
@login_required
def save_file():
    username = session['username']
    data = request.get_json()
    filename = data.get('filename')
    content = data.get('content')
    
    full_path = os.path.join(USERS_DIR, username, filename)
    with open(full_path, 'w') as f:
        f.write(content)
    
    return jsonify({'message': 'File saved successfully.'})

@app.route('/create', methods=['POST'])
@login_required
def create_item():
    username = session['username']
    data = request.get_json()
    name = data.get('name')
    path = data.get('path', '')
    item_type = data.get('type')

    full_path = os.path.join(USERS_DIR, username, path, name)
    
    if item_type == 'file':
        with open(full_path, 'w') as f:
            f.write('')
    elif item_type == 'folder':
        os.makedirs(full_path, exist_ok=True)
    
    return jsonify({'message': f'{item_type.capitalize()} created successfully'})

@app.route('/execute', methods=['POST'])
@login_required
def execute_code():
    data = request.get_json()
    content = data.get('content')

    if contains_forbidden_patterns(content):
        return jsonify({'output': 'Execution blocked due to dangerous code patterns.'})

    try:
        if platform.system() == 'Windows':
            linguagem = "python"
        else:
            linguagem = "python3"
        # Executa o código em um subprocesso
        result = subprocess.run([linguagem, '-c', content], capture_output=True, text=True)
        return jsonify({'output': result.stdout + result.stderr})
    except Exception as e:
        return jsonify({'output': str(e)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')