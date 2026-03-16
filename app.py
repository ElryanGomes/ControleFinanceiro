from flask import Flask, render_template, url_for, request, redirect, jsonify

app = Flask(__name__)

# Simulação de "Banco de Dados"
ganhos = []
gastos = []

@app.route('/')
def index():
    # Garante que os valores existam, mesmo que as listas estejam vazias
    t_entradas = sum(float(item.get('valor', 0)) for item in ganhos)
    t_saidas = sum(float(item.get('valor_mensal', 0)) for item in gastos)
    v_saldo = t_entradas - t_saidas
    
    return render_template(
        'index.html',
        ganhos=ganhos,
        gastos=gastos,
        total_entradas=t_entradas, # O nome aqui (total_entradas) deve ser o mesmo do {{ }} no HTML
        total_saidas=t_saidas,
        saldo=v_saldo
    )

@app.route('/atualizar_gasto', methods=['POST'])
def atualizar_gasto():
    idx = int(request.form.get('index'))
    novas_pagas = int(request.form.get('parcelas_pagas'))
    
    if 0 <= idx < len(gastos):
        item = gastos[idx]
        item['parcelas_pagas'] = novas_pagas
        
        # Recalcular valor restante
        item['falta_pagar'] = item['valor_total'] - (item['valor_mensal'] * novas_pagas)
        
        # Atualizar status geral se tudo foi pago
        if novas_pagas >= item['total_parcelas']:
            item['status'] = 'Pago'
        else:
            item['status'] = 'Pendente'
            
        return jsonify(success=True)
    
    return jsonify(success=False), 400


@app.route('/adicionar')
def adicionar():
    return render_template('adicionar.html')


@app.route('/adicionar_ganho', methods=['POST'])
def adicionar_ganho():
    nome = request.form.get('nome_ganho')
    try:
        valor = float(request.form.get('valor_ganho') or 0)
    except ValueError:
        valor = 0
    data = request.form.get('data_ganho')

    if nome and valor > 0:
        ganhos.append({'nome': nome, 'valor': valor, 'data': data})
    
    return redirect(url_for('index'))


@app.route('/adicionar_gasto', methods=['POST'])
def adicionar_gasto():
    nome = request.form.get('nome_item')
    categoria = request.form.get('categoria')
    tipo_pagamento = request.form.get('tipo_pagamento')
    status = request.form.get('status_pagamento') # Novo: Pega se é Pago, Reservado ou Pendente
    data = request.form.get('data_gasto')
    
    try:
        valor_total = float(request.form.get('valor_total') or 0)
    except ValueError:
        valor_total = 0

    dados_gasto = {
        'nome': nome,
        'valor_total': valor_total,
        'tipo': tipo_pagamento,
        'status': status,
        'data': data,
        'categoria': categoria
    }

    if tipo_pagamento == 'Parcelado':
        try:
            v_parcela = float(request.form.get('valor_parcela') or 0)
            p_pagas = int(request.form.get('parcelas_pagas') or 0)
            
            if v_parcela <= 0: v_parcela = valor_total
            total_p = int(valor_total / v_parcela) if v_parcela > 0 else 1
            
            dados_gasto.update({
                'valor_mensal': v_parcela,
                'parcelas_pagas': p_pagas,
                'total_parcelas': total_p,
                'falta_pagar': valor_total - (v_parcela * p_pagas)
            })
        except (ValueError, ZeroDivisionError):
            dados_gasto.update({'valor_mensal': valor_total, 'falta_pagar': 0})
    else:
        # Gasto único
        dados_gasto.update({
            'valor_mensal': valor_total,
            'falta_pagar': 0
        })

    if nome and valor_total > 0:
        gastos.append(dados_gasto)
    
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(port=5000, debug=True)