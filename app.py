from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
# from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Configuração do Banco de Dados
base_dir = os.path.abspath(os.path.dirname(__file__))
if 'elryan' in base_dir:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/elryan/projetoFinanceiro/financas.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'financas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELOS ---
class Ganho(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    valor = db.Column(db.Float)
    data = db.Column(db.String(20))
    mes = db.Column(db.Integer)
    ano = db.Column(db.Integer)

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    valor_total = db.Column(db.Float, nullable=False) # Valor da Reserva ou Total
    valor_mensal = db.Column(db.Float, nullable=False) # Valor da Parcela
    valor_gasto_real = db.Column(db.Float, default=0.0) # Quanto já usou do envelope
    total_parcelas = db.Column(db.Integer, default=1)
    parcelas_pagas = db.Column(db.Integer, default=0)
    parcelas_reservadas = db.Column(db.Integer, default=0) # Adicione esta linha
    falta_pagar = db.Column(db.Float)
    tipo = db.Column(db.String(20)) # 'Fixo', 'Parcelado' ou 'Unico'
    status = db.Column(db.String(20), default='Pendente')
    mes = db.Column(db.Integer)
    ano = db.Column(db.Integer)

def verificar_reset_mensal(user_id, dia_pagamento=10):
    hoje = datetime.now()
    
    # 1. Verifica se hoje é o dia do pagamento ou depois dele
    if hoje.day >= dia_pagamento:
        # 2. Busca no banco se o "mês atual" já foi processado
        # Se não foi, iniciamos o reset:
        
        # A. Apagar gastos "Únicos/Variáveis" do mês passado
        Gasto.query.filter_by(user_id=user_id, tipo='Unico').delete()
        
        # B. Resetar o 'valor_gasto_real' dos gastos FIXOS 
        # (Eles continuam lá, mas o progresso volta a zero)
        gastos_fixos = Gasto.query.filter_by(user_id=user_id, tipo='Fixo').all()
        for gasto in gastos_fixos:
            gasto.valor_gasto_real = 0
            gasto.status = 'Pendente'
            
        # C. Itens parcelados permanecem intactos (a lógica de parcelas 
        # que você já tem no HTML cuida do visual deles)
        
        db.session.commit()

with app.app_context():
    db.create_all()

# --- ROTAS ---

@app.route('/')
def index():
    # Pega mês e ano da URL. Se não existir, usa o atual.
    mes_selecionado = request.args.get('mes', datetime.now().month, type=int)
    ano_selecionado = request.args.get('ano', datetime.now().year, type=int)

    # Filtra GASTOS e GANHOS pelo mês/ano dos botões
    gastos = Gasto.query.filter_by(mes=mes_selecionado, ano=ano_selecionado).all()
    ganhos = Ganho.query.filter_by(mes=mes_selecionado, ano=ano_selecionado).all()
    
    total_recebido = sum(g.valor for g in ganhos)
    
    # 1. Gastos à Vista
    gastos_a_vista = sum(i.valor_total for i in gastos if i.tipo == 'Unico')
    
    # 2. Envelopes/Reservas Fixas
    reserva_envelopes = sum(i.valor_total for i in gastos if i.tipo == 'Fixo')
    
    # 3. Parcelas
    total_parcelas_comprometidas = 0
    for item in gastos:
        if item.tipo == 'Parcelado':
            quantidade_fora_do_bolso = (item.parcelas_pagas or 0) + (item.parcelas_reservadas or 0)
            total_parcelas_comprometidas += (item.valor_mensal * quantidade_fora_do_bolso)

    total_saidas = gastos_a_vista + reserva_envelopes + total_parcelas_comprometidas
    saldo_real_livre = total_recebido - total_saidas
    
    return render_template('index.html', 
                           gastos=gastos, 
                           ganhos=ganhos,
                           saldo=saldo_real_livre,
                           total_entradas=total_recebido,
                           total_saidas=total_saidas,
                           mes_ativo=mes_selecionado,
                           ano_ativo=ano_selecionado,
                           now=datetime.now())


@app.route('/adicionar_gasto', methods=['POST'])
def adicionar_gasto():
    nome = request.form.get('nome_item')
    categoria = request.form.get('categoria')
    tipo = request.form.get('tipo_pagamento')
    v_total = float(request.form.get('valor_total') or 0)
    
    # 1. Tenta pegar o mês e ano que você estava navegando no Dashboard
    # Se não encontrar (ex: você entrou direto no link), usa a data atual como plano B
    mes_contexto = request.form.get('mes_contexto', type=int)
    ano_contexto = request.form.get('ano_contexto', type=int)
    
    if not mes_contexto or not ano_contexto:
        hoje = datetime.now()
        mes_contexto = hoje.month
        ano_contexto = hoje.year
    
    v_mensal = v_total
    p_pagas = 0
    total_p = 1
    status = 'Pendente'

    if tipo == 'Unico':
        status = 'Pago'
        p_pagas = 1
    elif tipo == 'Parcelado':
        v_mensal = float(request.form.get('valor_parcela') or v_total)
        p_pagas = int(request.form.get('parcelas_pagas') or 0)
        total_p = int(v_total / v_mensal) if v_mensal > 0 else 1
        if p_pagas == total_p: status = 'Pago'

    novo_gasto = Gasto(
        nome=nome, 
        categoria=categoria, 
        valor_total=v_total,
        valor_mensal=v_mensal, 
        total_parcelas=total_p,
        parcelas_pagas=p_pagas, 
        tipo=tipo,
        falta_pagar=v_total - (v_mensal * p_pagas),
        status=status,
        mes=mes_contexto,  # <--- SALVA NO MÊS QUE VOCÊ ESTAVA VENDO
        ano=ano_contexto    # <--- SALVA NO ANO QUE VOCÊ ESTAVA VENDO
    )
    
    db.session.add(novo_gasto)
    db.session.commit()
    
    # Redireciona de volta para o Dashboard exatamente no mês/ano em que o item foi criado
    return redirect(url_for('index', mes=mes_contexto, ano=ano_contexto))


# ROTA PARA EXIBIR O FORMULÁRIO DE EDIÇÃO
@app.route('/editar_item/<int:id>')
def editar_item_view(id):
    item = Gasto.query.get_or_404(id)
    return render_template('editar_item.html', item=item)

# ROTA PARA PROCESSAR O SALVAMENTO (NOME DA FUNÇÃO ALTERADO)
@app.route('/salvar_edicao_base/<int:id>', methods=['POST'])
def salvar_edicao_base(id):
    gasto = Gasto.query.get_or_404(id)
    
    # Atualiza os dados básicos
    gasto.nome = request.form.get('nome')
    gasto.categoria = request.form.get('categoria')
    gasto.tipo = request.form.get('tipo')
    
    # Converte o valor para float
    novo_valor_total = float(request.form.get('valor_total'))
    
    # Se o valor total mudou, precisamos ajustar o valor_mensal proporcionalmente
    if gasto.tipo == 'Parcelado' and gasto.total_parcelas > 0:
        gasto.valor_total = novo_valor_total
        gasto.valor_mensal = novo_valor_total / gasto.total_parcelas
    else:
        gasto.valor_total = novo_valor_total
        gasto.valor_mensal = novo_valor_total

    try:
        db.session.commit()
        return redirect('/editar')  # Redireciona para a sua lista de gerenciamento
    except Exception as e:
        db.session.rollback()
        return f"Erro ao salvar: {e}", 500


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
    
    hoje = datetime.now() # DATA ATUAL
    
    if nome and valor > 0:
        novo = Ganho(
            nome=nome, 
            valor=valor, 
            mes=hoje.month, 
            ano=hoje.year 
        )
        db.session.add(novo)
        db.session.commit()
    return redirect(url_for('index'))



@app.route('/adicionar')
def adicionar():
    # Pega o mês/ano da URL ou usa o atual se não vier nada
    mes = request.args.get('mes', datetime.now().month, type=int)
    ano = request.args.get('ano', datetime.now().year, type=int)
    return render_template('adicionar.html', mes_selecionado=mes, ano_selecionado=ano)


@app.route('/atualizar_gasto', methods=['POST'])
def atualizar_gasto():
    gasto_id = request.form.get('id')
    p_pagas = int(request.form.get('parcelas_pagas') or 0)
    p_reservadas = int(request.form.get('parcelas_reservadas') or 0)
    
    gasto = Gasto.query.get(gasto_id)
    if gasto:
        gasto.parcelas_pagas = p_pagas
        gasto.parcelas_reservadas = p_reservadas
        
        # O total que saiu da conta para o saldo livre
        comprometido = p_pagas + p_reservadas
        gasto.falta_pagar = gasto.valor_total - (gasto.valor_mensal * comprometido)
        
        # Status visual do Card
        if p_pagas >= gasto.total_parcelas:
            gasto.status = 'Pago'
        elif p_reservadas > 0:
            gasto.status = 'Reservado' # Fica Amarelo!
        else:
            gasto.status = 'Pendente'
            
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False), 404




@app.route('/editar')
def editar():
    # Pega todos os gastos do banco para listar na tela de gerenciar
    gastos = Gasto.query.all() 
    return render_template('editar.html', gastos=gastos)

@app.route('/excluir_gasto/<int:id>', methods=['POST'])
def excluir_gasto(id):
    gasto = Gasto.query.get_or_404(id)
    try:
        db.session.delete(gasto)
        db.session.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    
@app.route('/historico')
def historico():
    # Pega os filtros da URL
    termo_busca = request.args.get('busca', '').lower()
    mes_filtro = request.args.get('mes_filtro', type=int)

    # Busca tudo
    gastos = Gasto.query.all()
    ganhos = Ganho.query.all()

    # Junta tudo em uma lista para facilitar
    todos_itens = []
    for g in gastos:
        todos_itens.append({'nome': g.nome, 'valor': g.valor_total, 'tipo': g.tipo, 'mes': g.mes, 'ano': g.ano, 'dia': g.dia if hasattr(g, 'dia') else '01', 'is_gasto': True})
    for g in ganhos:
        todos_itens.append({'nome': g.nome, 'valor': g.valor, 'tipo': 'Ganho', 'mes': g.mes, 'ano': g.ano, 'dia': g.dia if hasattr(g, 'dia') else '01', 'is_gasto': False})

    # Aplica Filtros de Pesquisa
    if termo_busca:
        todos_itens = [i for i in todos_itens if termo_busca in i['nome'].lower()]
    if mes_filtro:
        todos_itens = [i for i in todos_itens if i['mes'] == mes_filtro]

    # Agrupa por Mês/Ano: { (3, 2026): [itens], (2, 2026): [itens] }
    historico_agrupado = {}
    meses_nomes = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    # Ordena por data (mais recente primeiro)
    todos_itens.sort(key=lambda x: (x['ano'], x['mes']), reverse=True)

    for item in todos_itens:
        chave = f"{meses_nomes[item['mes']]} {item['ano']}"
        if chave not in historico_agrupado:
            historico_agrupado[chave] = []
        historico_agrupado[chave].append(item)

    return render_template('historico.html', historico=historico_agrupado, termo=termo_busca, mes_selecionado=mes_filtro)

@app.route('/progresso')
def progresso():
    meses_nomes = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    hoje = datetime.now()
    
    labels, dados_entradas, dados_saidas = [], [], []
    total_economia = 0
    mes_recorde_ganho = {"nome": "---", "valor": 0}
    mes_recorde_gasto = {"nome": "---", "valor": 0}

    # Analisamos os últimos 6 meses
    for i in range(5, -1, -1):
        # Lógica manual para voltar os meses
        m = hoje.month - i
        a = hoje.year
        while m <= 0:
            m += 12
            a -= 1
        
        entradas = sum(g.valor for g in Ganho.query.filter_by(mes=m, ano=a).all())
        saidas = sum(g.valor_total for g in Gasto.query.filter_by(mes=m, ano=a).all())
        economia = entradas - saidas
        
        labels.append(f"{meses_nomes[m]}/{a}")
        dados_entradas.append(float(entradas))
        dados_saidas.append(float(saidas))
        total_economia += economia

        # Verifica Recordes
        if entradas > mes_recorde_ganho["valor"]:
            mes_recorde_ganho = {"nome": f"{meses_nomes[m]}/{a}", "valor": entradas}
        if saidas > mes_recorde_gasto["valor"]:
            mes_recorde_gasto = {"nome": f"{meses_nomes[m]}/{a}", "valor": saidas}

    media_economia = total_economia / 6 if total_economia > 0 else 0

    return render_template('progresso.html', 
                           labels=labels, 
                           entradas=dados_entradas, 
                           saidas=dados_saidas,
                           media=media_economia,
                           recorde_ganho=mes_recorde_ganho,
                           recorde_gasto=mes_recorde_gasto)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)