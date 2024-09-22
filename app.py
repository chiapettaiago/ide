from flask import Flask, request, render_template_string, jsonify
import subprocess
import os
import re

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

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Browser IDE</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/theme/monokai.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/addon/hint/show-hint.min.css">
    <style>
        #file-tree { height: 400px; overflow-y: auto; }
        .folder { cursor: pointer; }
        .file { cursor: pointer; }
        .CodeMirror { height: 300px; }
        #output { height: 150px; }
    </style>
</head>
<body>
    <div class="container-fluid mt-3">
        <h1 class="mb-4 text-center">Browser IDE</h1>
        <div class="row">
            <div class="col-md-3">
                <h4>File Explorer</h4>
                <div id="file-tree" class="border p-2"></div>
                <div class="mt-2">
                    <input type="text" id="new-item-name" class="form-control" placeholder="New file/folder name">
                    <div class="mt-3" role="group">
                        <button onclick="createFile()" class="btn btn-primary mr-3">Create File</button>
                        <button onclick="createFolder()" class="btn btn-secondary">Create Folder</button>
                    </div>
                </div>
            </div>
            <div class="col-md-9">
                <div class="mb-3">
                    <label for="filename" class="form-label">Current File:</label>
                    <input type="text" id="filename" class="form-control" readonly>
                </div>
                <textarea id="editor"></textarea>
                <div class="mt-3">
                    <button onclick="saveFile()" class="btn btn-success">Save File</button>
                    <button onclick="executeCode()" class="btn btn-primary">Execute Code</button>
                </div>
                <textarea id="output" class="form-control mt-3 mb-3" readonly></textarea>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/python/python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/addon/hint/show-hint.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/addon/hint/anyword-hint.min.js"></script>
    <script>
        let currentFile = '';
        let currentPath = '';
        let editor;

         // Inicializa o CodeMirror
    document.addEventListener('DOMContentLoaded', (event) => {
        editor = CodeMirror.fromTextArea(document.getElementById("editor"), {
            mode: "python",
            theme: "monokai",
            lineNumbers: true,
            autoCloseBrackets: true,
            matchBrackets: true,
            indentUnit: 4,
            tabSize: 4,
            indentWithTabs: false,
            extraKeys: {
                "Ctrl-Space": "autocomplete"  // Atalho para o autocompletar manual
            }
        });

        // Ativar o autocompletar enquanto o usuário digita
        editor.on("inputRead", function(cm, event) {
            if (!cm.state.completionActive && event.text[0] !== ' ') { // Verifica se o autocompletar não está ativo
                cm.showHint({
                    hint: CodeMirror.hint.anyword,
                    completeSingle: false // Evita completar automaticamente com uma única sugestão
                });
            }
        });
    });

        function updateFileTree() {
            fetch('/files' + (currentPath ? `?path=${currentPath}` : ''))
                .then(response => response.json())
                .then(data => {
                    const fileTree = document.getElementById('file-tree');
                    fileTree.innerHTML = '';
                    if (currentPath) {
                        const backFolder = document.createElement('div');
                        backFolder.innerHTML = '<i class="bi bi-arrow-up"></i> ..';
                        backFolder.onclick = () => {
                            currentPath = currentPath.split('/').slice(0, -1).join('/');
                            updateFileTree();
                        };
                        fileTree.appendChild(backFolder);
                    }
                    data.folders.forEach(folder => {
                        const div = document.createElement('div');
                        div.className = 'folder';
                        div.innerHTML = `<i class="bi bi-folder"></i> ${folder}`;
                        div.onclick = () => {
                            currentPath = currentPath ? `${currentPath}/${folder}` : folder;
                            updateFileTree();
                        };
                        fileTree.appendChild(div);
                    });
                    data.files.forEach(file => {
                        const div = document.createElement('div');
                        div.className = 'file';
                        div.innerHTML = `<i class="bi bi-file-text"></i> ${file}`;
                        div.onclick = () => loadFile(file);
                        fileTree.appendChild(div);
                    });
                });
        }

        function loadFile(filename) {
            fetch(`/load/${currentPath ? currentPath + '/' : ''}${filename}`)
                .then(response => response.text())
                .then(content => {
                    editor.setValue(content);
                    document.getElementById('filename').value = filename;
                    currentFile = filename;
                });
        }

        function saveFile() {
            const content = editor.getValue();
            fetch('/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename: `${currentPath ? currentPath + '/' : ''}${currentFile}`, content})
            }).then(response => response.json())
              .then(data => {
                  alert(data.message);
                  updateFileTree();
              });
        }

        function createFile() {
            const filename = document.getElementById('new-item-name').value;
            if (filename) {
                fetch('/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: currentPath, name: filename, type: 'file'})
                }).then(response => response.json())
                  .then(data => {
                      alert(data.message);
                      updateFileTree();
                      document.getElementById('new-item-name').value = '';
                  });
            }
        }

        function createFolder() {
            const foldername = document.getElementById('new-item-name').value;
            if (foldername) {
                fetch('/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: currentPath, name: foldername, type: 'folder'})
                }).then(response => response.json())
                  .then(data => {
                      alert(data.message);
                      updateFileTree();
                      document.getElementById('new-item-name').value = '';
                  });
            }
        }

        function executeCode() {
            const content = editor.getValue();
            fetch('/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content})
            }).then(response => response.json())
              .then(data => {
                  const output = document.getElementById('output');
                  output.value = data.output;
              });
        }

        updateFileTree();
    </script>
</body>
</html>
'''

# Função para verificar padrões perigosos no código
def contains_forbidden_patterns(code):
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return True
    return False

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

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
    with open(full_path, 'w') as f:
        f.write(content)
    
    return jsonify({'message': 'File saved successfully'})

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
        # Executa o código em um subprocesso
        result = subprocess.run(['python', '-c', content], capture_output=True, text=True)
        return jsonify({'output': result.stdout + result.stderr})
    except Exception as e:
        return jsonify({'output': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
