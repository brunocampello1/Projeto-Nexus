from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Habito, RegistroHabito, Tarefa, Subtarefa
from datetime import date, timedelta, datetime
from sqlalchemy import text
from sqlalchemy.orm import joinedload

# Importando blueprint do módulo Financeiro
from templates.modules.Financeiro.routes import financeiro_bp

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Registrando blueprint
app.register_blueprint(financeiro_bp, url_prefix='/financeiro')

with app.app_context():
    db.create_all()

    # Auto-migração do SQLite para o campo de ordenação
    try:
        existing_columns = [row[1] for row in db.session.execute(text("PRAGMA table_info(tarefa);"))]
        if 'ordem' not in existing_columns:
            db.session.execute(text("ALTER TABLE tarefa ADD COLUMN ordem INTEGER DEFAULT 0 NOT NULL"))
            tarefas = db.session.execute(text("SELECT id FROM tarefa ORDER BY id")).fetchall()
            for idx, (tarefa_id,) in enumerate(tarefas):
                db.session.execute(text("UPDATE tarefa SET ordem = :ordem WHERE id = :id"), {'ordem': idx, 'id': tarefa_id})
            db.session.commit()
    except Exception:
        db.session.rollback()

    # Auto-migração: adicionar data_criacao em habito (padrão = hoje para registros existentes)
    try:
        habito_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(habito);"))]
        if 'data_criacao' not in habito_cols:
            hoje_str = date.today().isoformat()
            db.session.execute(text(f"ALTER TABLE habito ADD COLUMN data_criacao DATE DEFAULT '{hoje_str}' NOT NULL"))
            db.session.commit()
    except Exception:
        db.session.rollback()

# ==========================================
# FUNÇÕES AUXILIARES - KPIs
# ==========================================
def calcular_streak_registros(registros):
    """Calcula a sequência de dias consecutivos concluídos (streak) de trás para frente"""
    concluidos = {reg.data for reg in registros if reg.concluido}
    if not concluidos:
        return 0
        
    hoje = date.today()
    streak = 0
    data_esperada = hoje
    
    if hoje in concluidos:
        while data_esperada in concluidos:
            streak += 1
            data_esperada -= timedelta(days=1)
    elif (hoje - timedelta(days=1)) in concluidos:
        data_esperada = hoje - timedelta(days=1)
        while data_esperada in concluidos:
            streak += 1
            data_esperada -= timedelta(days=1)
            
    return streak


def calcular_kpis_habitos(lista_habitos, dias):
    """Calcula métricas de desempenho dos hábitos.
    
    - taxa_conclusao_geral: % concluído desde a criação até hoje (período real)
    - Por hábito: conclusoes = dias concluídos na janela 'dias' (semana visível)
                  total_periodo = dias desde criação até 31/12 do ano atual
                  taxa = conclusoes_totais / total_periodo * 100
    """
    kpis = {
        'taxa_conclusao_geral': 0,
        'melhor_habito': None,
        'habitos_por_performance': [],
        'taxa_cumprimento_metas': 0,
        'streaks': {},
        'periodo_label': ''
    }

    if not lista_habitos:
        return kpis

    hoje = date.today()
    fim_ano = date(hoje.year, 12, 31)

    total_conclusoes_global = 0
    total_possiveis_global = 0
    metas_cumpridas = 0

    # Janela de dias visível na tabela (para marcar o checkbox)
    set_dias = set(dias)

    for habito in lista_habitos:
        # Período completo do hábito: criação → 31/12
        inicio_habito = habito.data_criacao
        total_periodo = (fim_ano - inicio_habito).days + 1  # inclusive
        if total_periodo < 1:
            total_periodo = 1

        # Todos os dias concluídos (histórico completo)
        todos_concluidos = {reg.data for reg in habito.registros if reg.concluido}
        conclusoes_total = len(todos_concluidos)

        # Conclusões na semana visível (para exibir na tabela e ranking)
        conclusoes_semana = sum(1 for reg in habito.registros if reg.data in set_dias and reg.concluido)

        # Taxa geral do período real
        taxa_periodo = int((conclusoes_total / total_periodo) * 100)

        # Streak
        streak = calcular_streak_registros(habito.registros)
        kpis['streaks'][str(habito.id)] = streak

        # Meta semanal (dias concluídos na semana visível vs meta)
        meta_atingida = conclusoes_semana >= habito.meta_dias
        if meta_atingida:
            metas_cumpridas += 1

        total_conclusoes_global += conclusoes_total
        total_possiveis_global += total_periodo

        dias_restantes = (fim_ano - hoje).days

        kpis['habitos_por_performance'].append({
            'id': habito.id,
            'nome': habito.nome,
            'taxa': taxa_periodo,
            'conclusoes': conclusoes_total,
            'conclusoes_semana': conclusoes_semana,
            'total_periodo': total_periodo,
            'meta_dias': habito.meta_dias,
            'meta_atingida': meta_atingida,
            'streak': streak,
            'data_criacao': inicio_habito.strftime('%d/%m/%Y'),
            'dias_restantes': dias_restantes,
        })

    # Ordenar por taxa do período
    kpis['habitos_por_performance'].sort(key=lambda x: x['taxa'], reverse=True)

    # Melhor hábito
    if kpis['habitos_por_performance']:
        melhor = kpis['habitos_por_performance'][0]
        if melhor['taxa'] > 0:
            kpis['melhor_habito'] = melhor

    # Taxa geral: total concluído / total possível (todos os hábitos, período real)
    kpis['taxa_conclusao_geral'] = int((total_conclusoes_global / total_possiveis_global) * 100) if total_possiveis_global > 0 else 0

    # Taxa de cumprimento de metas (semana visível)
    total_metas = len(lista_habitos)
    kpis['taxa_cumprimento_metas'] = int((metas_cumpridas / total_metas) * 100) if total_metas > 0 else 0

    return kpis



def calcular_tendencia(lista_habitos):
    """Compara performance desta semana com a anterior"""
    hoje = date.today()
    semana_atual = [hoje - timedelta(days=i) for i in range(6, -1, -1)]
    semana_passada = [hoje - timedelta(days=i) for i in range(13, 6, -1)]
    
    conclusoes_atual = sum(
        1 for habito in lista_habitos 
        for reg in habito.registros 
        if reg.data in semana_atual and reg.concluido
    )
    
    conclusoes_passada = sum(
        1 for habito in lista_habitos 
        for reg in habito.registros 
        if reg.data in semana_passada and reg.concluido
    )
    
    total_possiveis = len(lista_habitos) * 7
    taxa_atual = (conclusoes_atual / total_possiveis * 100) if total_possiveis > 0 else 0
    taxa_passada = (conclusoes_passada / total_possiveis * 100) if total_possiveis > 0 else 0
    
    diferenca = taxa_atual - taxa_passada
    
    return {
        'taxa_atual': int(taxa_atual),
        'taxa_passada': int(taxa_passada),
        'diferenca': int(diferenca),
        'direcao': 'up' if diferenca > 0 else ('down' if diferenca < 0 else 'stable')
    }


# ==========================================
# MÓDULO: HÁBITOS
# ==========================================
@app.route('/')
def habitos():
    try:
        week_offset = int(request.args.get('week_offset', 0))
    except ValueError:
        week_offset = 0

    lista_habitos = Habito.query.options(joinedload(Habito.registros)).order_by(Habito.nome).all()
    hoje = date.today()
    domingo = hoje - timedelta(days=(hoje.weekday() + 1) % 7)
    domingo_ativo = domingo + timedelta(weeks=week_offset)
    dias = [domingo_ativo + timedelta(days=i) for i in range(7)]
    
    # Calcular KPIs
    kpis = calcular_kpis_habitos(lista_habitos, dias)
    tendencia = calcular_tendencia(lista_habitos)
    
    return render_template('modules/Produtividade/habitos.html', habitos=lista_habitos, dias=dias, kpis=kpis, tendencia=tendencia, week_offset=week_offset, now=hoje)

@app.route('/add_habito', methods=['POST'])
def add_habito():
    nome = request.form.get('nome')
    if nome:
        novo_habito = Habito(nome=nome)
        db.session.add(novo_habito)
        db.session.commit()
    return redirect(url_for('habitos'))

@app.route('/toggle_habito/<int:habito_id>/<data_str>', methods=['POST'])
def toggle_habito(habito_id, data_str):
    data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
    registro = RegistroHabito.query.filter_by(habito_id=habito_id, data=data_obj).first()

    if registro:
        registro.concluido = not registro.concluido
    else:
        registro = RegistroHabito(habito_id=habito_id, data=data_obj, concluido=True)
        db.session.add(registro)

    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Recalcular KPIs para retornar atualizado
        try:
            week_offset = int(request.args.get('week_offset', 0))
        except ValueError:
            week_offset = 0
            
        lista_habitos = Habito.query.options(joinedload(Habito.registros)).order_by(Habito.nome).all()
        hoje = date.today()
        domingo = hoje - timedelta(days=(hoje.weekday() + 1) % 7)
        domingo_ativo = domingo + timedelta(weeks=week_offset)
        dias = [domingo_ativo + timedelta(days=i) for i in range(7)]
        kpis = calcular_kpis_habitos(lista_habitos, dias)
        tendencia = calcular_tendencia(lista_habitos)
        
        return jsonify({
            'concluido': registro.concluido,
            'data': data_str,
            'habito_id': habito_id,
            'kpis': kpis,
            'tendencia': tendencia
        })

    return redirect(url_for('habitos'))

# NOVO: Rota para excluir hábito
@app.route('/delete_habito/<int:habito_id>', methods=['POST'])
def delete_habito(habito_id):
    habito = Habito.query.get_or_404(habito_id)
    db.session.delete(habito)
    db.session.commit()
    return redirect(url_for('habitos'))

# NOVO: Rota para atualizar meta de hábito
@app.route('/update_meta_habito/<int:habito_id>/<int:meta_dias>', methods=['POST'])
def update_meta_habito(habito_id, meta_dias):
    habito = Habito.query.get_or_404(habito_id)
    
    # Validar meta (deve estar entre 0 e 7)
    if 0 <= meta_dias <= 7:
        habito.meta_dias = meta_dias
        db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Recalcular KPIs para retornar atualizado
        try:
            week_offset = int(request.args.get('week_offset', 0))
        except ValueError:
            week_offset = 0
            
        lista_habitos = Habito.query.options(joinedload(Habito.registros)).order_by(Habito.nome).all()
        hoje = date.today()
        domingo = hoje - timedelta(days=(hoje.weekday() + 1) % 7)
        domingo_ativo = domingo + timedelta(weeks=week_offset)
        dias = [domingo_ativo + timedelta(days=i) for i in range(7)]
        kpis = calcular_kpis_habitos(lista_habitos, dias)
        tendencia = calcular_tendencia(lista_habitos)
        
        return jsonify({
            'success': True,
            'meta_dias': habito.meta_dias,
            'kpis': kpis,
            'tendencia': tendencia
        })
    
    return redirect(url_for('habitos'))


@app.route('/habito/<int:habito_id>/history')
def habito_history(habito_id):
    habito = Habito.query.options(joinedload(Habito.registros)).get_or_404(habito_id)
    
    hoje = date.today()
    # Queremos os últimos 30 dias (inclusive hoje)
    inicio = hoje - timedelta(days=29)
    
    # Criar um conjunto de datas concluídas
    registros_concluidos = {reg.data for reg in habito.registros if reg.concluido}
    
    history_list = []
    for i in range(30):
        dia = inicio + timedelta(days=i)
        dia_str = dia.strftime('%Y-%m-%d')
        history_list.append({
            'data': dia_str,
            'dia_mes': dia.strftime('%d/%m'),
            'concluido': dia in registros_concluidos
        })
        
    streak = calcular_streak_registros(habito.registros)
    total_concluidos = sum(1 for item in history_list if item['concluido'])
    taxa_sucesso = int((total_concluidos / 30) * 100)
    
    return jsonify({
        'id': habito.id,
        'nome': habito.nome,
        'history': history_list,
        'streak': streak,
        'total_concluidos': total_concluidos,
        'taxa_sucesso': taxa_sucesso
    })


# ==========================================
# MÓDULO: TAREFAS
# ==========================================
@app.route('/tarefas')
def tarefas():
    lista_tarefas = Tarefa.query.options(joinedload(Tarefa.subtarefas)).order_by(Tarefa.ordem).all()
    return render_template('modules/Produtividade/tarefas.html', tarefas=lista_tarefas)

@app.route('/add_tarefa', methods=['POST'])
def add_tarefa():
    titulo = request.form.get('titulo')
    if titulo:
        # Atribui ordem sequencial ao criar nova tarefa
        max_ordem = db.session.query(db.func.max(Tarefa.ordem)).scalar() or 0
        nova_tarefa = Tarefa(titulo=titulo, ordem=(max_ordem + 1))
        db.session.add(nova_tarefa)
        db.session.commit()
    return redirect(url_for('tarefas'))

@app.route('/add_subtarefa/<int:tarefa_id>', methods=['POST'])
def add_subtarefa(tarefa_id):
    descricao = request.form.get('descricao')
    if descricao:
        tarefa = Tarefa.query.get_or_404(tarefa_id)
        ordem_atual = len(tarefa.subtarefas)
        nova_sub = Subtarefa(descricao=descricao, tarefa_id=tarefa.id, ordem=ordem_atual)
        db.session.add(nova_sub)
        db.session.commit()
    return redirect(url_for('tarefas'))

@app.route('/toggle_subtarefa/<int:subtarefa_id>', methods=['POST'])
def toggle_subtarefa(subtarefa_id):
    subtarefa = Subtarefa.query.get_or_404(subtarefa_id)
    subtarefa.concluida = not subtarefa.concluida
    db.session.commit()

    progresso = subtarefa.tarefa.progresso
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'subtarefa_id': subtarefa_id,
            'concluida': subtarefa.concluida,
            'tarefa_id': subtarefa.tarefa.id,
            'progresso': progresso
        })

    return redirect(url_for('tarefas'))

# NOVO: Rota para excluir tarefa principal
@app.route('/delete_tarefa/<int:tarefa_id>', methods=['POST'])
def delete_tarefa(tarefa_id):
    tarefa = Tarefa.query.get_or_404(tarefa_id)
    db.session.delete(tarefa)
    db.session.commit()
    return redirect(url_for('tarefas'))

# NOVO: Rota para excluir subtarefa
@app.route('/delete_subtarefa/<int:subtarefa_id>', methods=['POST'])
def delete_subtarefa(subtarefa_id):
    subtarefa = Subtarefa.query.get_or_404(subtarefa_id)
    db.session.delete(subtarefa)
    db.session.commit()
    return redirect(url_for('tarefas'))

# NOVO: Rota para atualizar status da tarefa
@app.route('/update_tarefa_status/<int:tarefa_id>/<status>', methods=['POST'])
def update_tarefa_status(tarefa_id, status):
    tarefa = Tarefa.query.get_or_404(tarefa_id)
    status_validos = ['em-andamento', 'refinamento', 'concluida', 'pendente-base']
    
    if status in status_validos:
        tarefa.status = status
        db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'tarefa_id': tarefa_id,
            'status': tarefa.status,
            'success': True
        })
    
    return redirect(url_for('tarefas'))


@app.route('/reorder_tarefas', methods=['POST'])
def reorder_tarefas():
    data = request.get_json() or {}
    order = data.get('order', [])

    # Espera uma lista de ids
    if not isinstance(order, list):
        return jsonify({'success': False, 'error': 'Formato inválido'}), 400

    try:
        for idx, tarefa_id in enumerate(order):
            tarefa = Tarefa.query.get(tarefa_id)
            if tarefa:
                tarefa.ordem = idx
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)