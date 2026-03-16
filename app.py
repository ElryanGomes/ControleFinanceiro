from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Configuração do Banco de Dados
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'financas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELOS ---
class Ganho(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    valor = db.Column(db.Float)
    data = db.Column(db.String(20))

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    valor_total = db.Column(db.Float, nullable=False) # Valor da Reserva ou Total
    valor_mensal = db.Column(db.Float, nullable=False) # Valor da Parcela
    valor_gasto_real = db.Column(db.Float, default=0.0) # Quanto já usou do envelope
    total_parcelas = db.Column(db.Integer, default=1)
    parcelas_pagas = db.Column(db.Integer, default=0)
    falta_pagar = db.Column(db.Float)
    tipo = db.Column(db.String(20)) # 'Fixo', 'Parcelado' ou 'Unico'
    status = db.Column(db.String(20), default='Pendente')

with app.app_context():
    db.create_all()

# --- ROTAS ---

@app.route('/')
def index():
    gastos = Gasto.query.all()
    ganhos = Ganho.query.all()
    
    total_recebido = sum(g.valor for g in ganhos)
    
    # CÁLCULO ATUALIZADO:
    # 1. Reservas (O que você "carimbou" para usar depois)
    reserva_envelopes = sum(i.valor_total for i in gastos if i.tipo == 'Fixo')
    # 2. Parcelas do Mês (O que vence agora)
    compromisso_parcelas = sum(i.valor_mensal for i in gastos if i.tipo == 'Parcelado')
    # 3. À Vista (O que já saiu da conta totalmente)
    gastos_a_vista = sum(i.valor_total for i in gastos if i.tipo == 'Unico')
    
    total_saidas = reserva_envelopes + compromisso_parcelas + gastos_a_vista
    saldo_real_livre = total_recebido - total_saidas
    
    return render_template('index.html', 
                           gastos=gastos, 
                           total_entradas=total_recebido,
                           total_saidas=total_saidas,
                           saldo=saldo_real_livre)

@app.route('/adicionar_gasto', methods=['POST'])
def adicionar_gasto():
    nome = request.form.get('nome_item')
    categoria = request.form.get('categoria')
    tipo = request.form.get('tipo_pagamento')
    v_total = float(request.form.get('valor_total') or 0)
    
    # Valores padrão
    v_mensal = v_total
    p_pagas = 0
    total_p = 1
    status = 'Pendente'

    # Se for À Vista, já nasce pago
    if tipo == 'Unico':
        status = 'Pago'
        p_pagas = 1
    
    elif tipo == 'Parcelado':
        v_mensal = float(request.form.get('valor_parcela') or v_total)
        p_pagas = int(request.form.get('parcelas_pagas') or 0)
        total_p = int(v_total / v_mensal) if v_mensal > 0 else 1
        if p_pagas == total_p: status = 'Pago'

    novo_gasto = Gasto(
        nome=nome, categoria=categoria, valor_total=v_total,
        valor_mensal=v_mensal, total_parcelas=total_p,
        parcelas_pagas=p_pagas, tipo=tipo,
        falta_pagar=v_total - (v_mensal * p_pagas),
        status=status
    )
    db.session.add(novo_gasto)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/abater_gasto', methods=['POST'])
def abater_gasto():
    gasto_id = request.form.get('id')
    valor_abatido = float(request.form.get('valor_abatido') or 0)
    gasto = Gasto.query.get(gasto_id)
    if gasto:
        gasto.valor_gasto_real = (gasto.valor_gasto_real or 0) + valor_abatido
        if gasto.valor_gasto_real >= gasto.valor_total:
            gasto.status = 'Concluído'
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False), 404

@app.route('/adicionar_ganho', methods=['POST'])
def adicionar_ganho():
    nome = request.form.get('nome_ganho')
    valor = float(request.form.get('valor_ganho') or 0)
    if nome and valor > 0:
        novo = Ganho(nome=nome, valor=valor)
        db.session.add(novo)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/adicionar')
def adicionar():
    return render_template('adicionar.html')

if __name__ == "__main__":
    app.run(debug=True)