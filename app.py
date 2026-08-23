from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Habito, RegistroHabito, Tarefa, Subtarefa, ItemRotina
from datetime import date, timedelta, datetime
from sqlalchemy import text
from sqlalchemy.orm import joinedload
import os

# Importando blueprint do módulo Financeiro
from templates.modules.Financeiro.routes import financeiro_bp

app = Flask(__name__)

# Configura o banco de dados via variável de ambiente (Render) ou usa o SQLite local como fallback
database_url = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Registrando blueprint
app.register_blueprint(financeiro_bp, url_prefix='/financeiro')

with app.app_context():
    # Auto-migração da Rotina: recriar se usar o esquema antigo 'horario' ou faltar 'is_bloqueio'
    try:
        rotina_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(item_rotina);"))]
        if rotina_cols and ('horario_inicio' not in rotina_cols or 'is_bloqueio' not in rotina_cols):
            db.session.execute(text("DROP TABLE item_rotina"))
            db.session.commit()
    except Exception:
        db.session.rollback()

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
# MÓDULO: ROTINA
# ==========================================
@app.route('/rotina')
def rotina():
    itens_rotina = ItemRotina.query.options(joinedload(ItemRotina.habito)).all()
    
    # Calcular KPIs
    # Planner vai das 00:00 até 24:00 (24 horas = 1440 minutos)
    total_minutos_dia = 24 * 60
    minutos_ocupados = 0
    
    for item in itens_rotina:
        try:
            h_ini, m_ini = map(int, item.horario_inicio.split(':'))
            h_fim, m_fim = map(int, item.horario_fim.split(':'))
            minutos = (h_fim * 60 + m_fim) - (h_ini * 60 + m_ini)
            if minutos > 0:
                minutos_ocupados += minutos
                
            # Planner config: 00:00 to 24:00 (1440 minutes)
            start_min = h_ini * 60 + m_ini
            end_min = max(start_min + 15, h_fim * 60 + m_fim) # minimo 15min de duração
            item.css_top = (start_min / 1440.0) * 100
            item.css_height = ((end_min - start_min) / 1440.0) * 100
            
            dur_mins = end_min - start_min
            h_dur = dur_mins // 60
            m_dur = dur_mins % 60
            if h_dur > 0 and m_dur > 0:
                item.duracao_str = f"{int(h_dur)}h {int(m_dur)}min"
            elif h_dur > 0:
                item.duracao_str = f"{int(h_dur)}h"
            else:
                item.duracao_str = f"{int(m_dur)}min"
            
        except Exception as e:
            print("Erro no item", e)
            item.css_top = 0
            item.css_height = (60 / 1440.0) * 100
            item.duracao_str = "1h"
            
        item.nome_display = item.titulo if item.is_bloqueio else (item.habito.nome if item.habito else "Sem Nome")
            
    horas_ocupadas = round(minutos_ocupados / 60, 1)
    horas_livres = round((total_minutos_dia - minutos_ocupados) / 60, 1)
    if horas_livres < 0: horas_livres = 0
    
    kpis = {
        'horas_ocupadas': horas_ocupadas,
        'horas_livres': horas_livres
    }

    return render_template('modules/Produtividade/rotina.html', itens_rotina=itens_rotina, kpis=kpis)

@app.route('/add_item_rotina', methods=['POST'])
def add_item_rotina():
    horario_inicio = request.form.get('horario_inicio')
    horario_fim = request.form.get('horario_fim')
    habito_nome = request.form.get('habito_nome')
    is_bloqueio = request.form.get('is_bloqueio') == 'on'
    
    if horario_inicio and horario_fim and habito_nome:
        if is_bloqueio:
            novo_item = ItemRotina(horario_inicio=horario_inicio, horario_fim=horario_fim, is_bloqueio=True, titulo=habito_nome)
            db.session.add(novo_item)
        else:
            habito = Habito.query.filter_by(nome=habito_nome).first()
            if not habito:
                habito = Habito(nome=habito_nome)
                db.session.add(habito)
                db.session.flush()
                
            novo_item = ItemRotina(horario_inicio=horario_inicio, horario_fim=horario_fim, habito_id=habito.id)
            db.session.add(novo_item)
            
        db.session.commit()
        
    return redirect(url_for('rotina'))

@app.route('/update_item_rotina/<int:item_id>', methods=['POST'])
def update_item_rotina(item_id):
    item = ItemRotina.query.get_or_404(item_id)
    
    if request.is_json:
        data = request.get_json()
        if 'horario_inicio' in data:
            item.horario_inicio = data['horario_inicio']
        if 'horario_fim' in data:
            item.horario_fim = data['horario_fim']
    else:
        # Form submission via modal
        item.horario_inicio = request.form.get('horario_inicio', item.horario_inicio)
        item.horario_fim = request.form.get('horario_fim', item.horario_fim)
        
        habito_nome = request.form.get('habito_nome')
        is_bloqueio = request.form.get('is_bloqueio') == 'on'
        
        if habito_nome:
            if is_bloqueio:
                item.is_bloqueio = True
                item.titulo = habito_nome
                item.habito_id = None
            else:
                item.is_bloqueio = False
                item.titulo = None
                if not item.habito or item.habito.nome != habito_nome:
                    # Check if new habit exists
                    habito = Habito.query.filter_by(nome=habito_nome).first()
                    if not habito:
                        habito = Habito(nome=habito_nome)
                        db.session.add(habito)
                        db.session.flush()
                    item.habito_id = habito.id

    db.session.commit()
    
    if request.is_json:
        return jsonify({'success': True})
    return redirect(url_for('rotina'))

@app.route('/delete_item_rotina/<int:item_id>', methods=['POST'])
def delete_item_rotina(item_id):
    item = ItemRotina.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True})
    return redirect(url_for('rotina'))

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