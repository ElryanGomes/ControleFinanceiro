from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Configuração do Banco de Dados SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'financas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo para Ganhos (Entradas)
class Ganho(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    valor = db.Column(db.Float)
    data = db.Column(db.String(20))

# Modelo para Gastos (Saídas)
class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    valor_mensal = db.Column(db.Float, nullable=False)
    total_parcelas = db.Column(db.Integer, default=1)
    parcelas_pagas = db.Column(db.Integer, default=0)
    falta_pagar = db.Column(db.Float)
    tipo = db.Column(db.String(20)) # 'Parcelado' ou 'Unico'
    status = db.Column(db.String(20), default='Pendente')

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    lista_ganhos = Ganho.query.all()
    lista_gastos = Gasto.query.all()
    
    t_entradas = sum(item.valor for item in lista_ganhos)
    t_saidas = sum(item.valor_mensal for item in lista_gastos)
    v_saldo = t_entradas - t_saidas
    
    return render_template(
        'index.html',
        ganhos=lista_ganhos,
        gastos=lista_gastos,
        total_entradas=t_entradas,
        total_saidas=t_saidas,
        saldo=v_saldo
    )

@app.route('/adicionar')
def adicionar():
    return render_template('adicionar.html')

@app.route('/adicionar_ganho', methods=['POST'])
def adicionar_ganho():
    nome = request.form.get('nome_ganho')
    valor = float(request.form.get('valor_ganho') or 0)
    data = request.form.get('data_ganho')

    if nome and valor > 0:
        novo_ganho = Ganho(nome=nome, valor=valor, data=data)
        db.session.add(novo_ganho)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/adicionar_gasto', methods=['POST'])
def adicionar_gasto():
    nome = request.form.get('nome_item')
    categoria = request.form.get('categoria')
    tipo = request.form.get('tipo_pagamento')
    v_total = float(request.form.get('valor_total') or 0)
    
    v_mensal = v_total
    p_pagas = 0
    total_p = 1

    if tipo == 'Parcelado':
        v_mensal = float(request.form.get('valor_parcela') or v_total)
        p_pagas = int(request.form.get('parcelas_pagas') or 0)
        total_p = int(v_total / v_mensal) if v_mensal > 0 else 1

    novo_gasto = Gasto(
        nome=nome, categoria=categoria, valor_total=v_total,
        valor_mensal=v_mensal, total_parcelas=total_p,
        parcelas_pagas=p_pagas, tipo=tipo,
        falta_pagar=v_total - (v_mensal * p_pagas),
        status='Pendente'
    )
    db.session.add(novo_gasto)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/atualizar_gasto', methods=['POST'])
def atualizar_gasto():
    gasto_id = request.form.get('id') # Mudado de 'index' para 'id'
    novas_pagas = int(request.form.get('parcelas_pagas'))
    gasto = Gasto.query.get(gasto_id)
    
    if gasto:
        gasto.parcelas_pagas = novas_pagas
        gasto.falta_pagar = gasto.valor_total - (gasto.valor_mensal * novas_pagas)
        gasto.status = 'Pago' if novas_pagas >= gasto.total_parcelas else 'Pendente'
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False), 404

if __name__ == "__main__":
    app.run(port=5000, debug=True)