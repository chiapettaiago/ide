from flask import Flask, request, render_template, jsonify
import subprocess
import os
import re
import platform

app = Flask(__name__)

USER_FILES_DIR = 'user_files'
if not os.path.exists(USER_FILES_DIR):
    os.makedirs(USER_FILES_DIR)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/files', methods=['GET'])
def list_files():
    path = request.args.get('path', '')
    full_path = os.path.join(USER_FILES_DIR, path)
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'Path does not exist'}), 400

    files = [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]
    folders = [f for f in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, f))]
    
    return jsonify({'files': files, 'folders': folders})

@app.route('/load/<path:filename>', methods=['GET'])
def load_file(filename):
    full_path = os.path.join(USER_FILES_DIR, filename)
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            return f.read()
    return '', 404

@app.route('/save', methods=['POST'])
def save_file():
    data = request.get_json()
    filename = data.get('filename')
    content = data.get('content')
    
    full_path = os.path.join(USER_FILES_DIR, filename)
    if full_path == "user_files\\" or full_path == 'user_files/':
        return jsonify({'message': 'Nenhum arquivo foi criado.'})
    else:
        with open(full_path, 'w') as f:
            f.write(content)
        
        return jsonify({'message': 'Arquivo salvo com sucesso.'})

@app.route('/create', methods=['POST'])
def create_item():
    data = request.get_json()
    name = data.get('name')
    path = data.get('path', '')
    item_type = data.get('type')

    full_path = os.path.join(USER_FILES_DIR, path, name)
    
    if item_type == 'file':
        with open(full_path, 'w') as f:
            f.write('')
    elif item_type == 'folder':
        os.makedirs(full_path, exist_ok=True)
    
    return jsonify({'message': f'{item_type.capitalize()} created successfully'})

@app.route('/execute', methods=['POST'])
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
    app.run(debug=True, host='0.0.0.0')
