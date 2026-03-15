from flask import Flask, render_template, url_for, request

app = Flask(__name__)

@app.route('/')
def index():
    # Renderiza o Dashboard
    return render_template('index.html')

@app.route('/editar')
def editar():
    # Renderiza a página de edição/cadastro
    return render_template('editar.html')

if __name__ == "__main__":
    # debug=True reinicia o servidor automaticamente ao salvar o arquivo
    app.run(port=5000, debug=True)