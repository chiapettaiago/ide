from flask import Flask, request, render_template_string, jsonify
import subprocess
import os

app = Flask(__name__)

USER_FILES_DIR = 'user_files'
if not os.path.exists(USER_FILES_DIR):
    os.makedirs(USER_FILES_DIR)

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

        // Initialize CodeMirror
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
                extraKeys: {"Ctrl-Space": "autocomplete"}
            });

            editor.on("inputRead", function(editor, change) {
                if (change.origin !== "+input") return;
                var cur = editor.getCursor();
                var token = editor.getTokenAt(cur);
                if (token.type === "variable" || token.string.trim() !== "") {
                    editor.showHint({
                        completeSingle: false,
                        hint: function(editor) {
                            var cursor = editor.getCursor();
                            var token = editor.getTokenAt(cursor);
                            var start = token.start;
                            var end = cursor.ch;
                            var line = cursor.line;
                            var currentWord = token.string;

                            var wordList = [
                                "def", "class", "if", "else", "elif", "for", "while", "try", "except",
                                "import", "from", "as", "return", "print", "len", "range", "int", "str",
                                "float", "list", "dict", "set", "tuple", "True", "False", "None"
                            ];

                            var result = wordList.filter(function(item) {
                                return item.indexOf(currentWord) === 0;
                            });

                            return {
                                list: result,
                                from: CodeMirror.Pos(line, start),
                                to: CodeMirror.Pos(line, end)
                            };
                        }
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
                  document.getElementById('output').value = data.output;
              });
        }

        updateFileTree();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/files')
def list_files():
    path = request.args.get('path', '')
    full_path = os.path.join(USER_FILES_DIR, path)
    files = []
    folders = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        if os.path.isfile(item_path):
            files.append(item)
        elif os.path.isdir(item_path):
            folders.append(item)
    return jsonify({"files": files, "folders": folders})

@app.route('/load/<path:filename>')
def load_file(filename):
    file_path = os.path.join(USER_FILES_DIR, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            return f.read()
    return "File not found", 404

@app.route('/save', methods=['POST'])
def save_file():
    data = request.json
    filename = data['filename']
    content = data['content']
    
    file_path = os.path.join(USER_FILES_DIR, filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(content)
    
    return jsonify({"message": f"File {filename} saved successfully"})

@app.route('/create', methods=['POST'])
def create_item():
    data = request.json
    path = data.get('path', '')
    name = data['name']
    item_type = data['type']
    
    full_path = os.path.join(USER_FILES_DIR, path, name)
    
    if item_type == 'file':
        if not os.path.exists(full_path):
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            open(full_path, 'a').close()
            return jsonify({"message": f"File {name} created successfully"})
        else:
            return jsonify({"message": f"File {name} already exists"}), 400
    elif item_type == 'folder':
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            return jsonify({"message": f"Folder {name} created successfully"})
        else:
            return jsonify({"message": f"Folder {name} already exists"}), 400
    else:
        return jsonify({"message": "Invalid item type"}), 400

@app.route('/execute', methods=['POST'])
def execute_code():
    data = request.json
    content = data['content']
    
    temp_file = os.path.join(USER_FILES_DIR, 'temp_code.py')
    with open(temp_file, 'w') as f:
        f.write(content)
    
    try:
        result = subprocess.run(['python', temp_file], capture_output=True, text=True, timeout=5)
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        output = "Execution timed out after 5 seconds"
    except Exception as e:
        output = str(e)
    
    os.remove(temp_file)
    
    return jsonify({"output": output})

if __name__ == '__main__':
    app.run(debug=True)