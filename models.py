from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()

# ==========================================
# MÓDULO 1: HÁBITOS
# ==========================================
class Habito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    meta_dias = db.Column(db.Integer, default=7, nullable=False)  # Meta de dias por semana (0-7)
    data_criacao = db.Column(db.Date, default=date.today, nullable=False)
    registros = db.relationship('RegistroHabito', backref='habito', lazy=True, cascade="all, delete-orphan")
    rotina_itens = db.relationship('ItemRotina', backref='habito', lazy=True, cascade="all, delete-orphan")

class RegistroHabito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, default=date.today, nullable=False)
    concluido = db.Column(db.Boolean, default=False)
    habito_id = db.Column(db.Integer, db.ForeignKey('habito.id'), nullable=False)

class ItemRotina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    horario_inicio = db.Column(db.String(5), nullable=False, default="08:00")
    horario_fim = db.Column(db.String(5), nullable=False, default="09:00")
    habito_id = db.Column(db.Integer, db.ForeignKey('habito.id'), nullable=True)
    titulo = db.Column(db.String(100), nullable=True)
    is_bloqueio = db.Column(db.Boolean, default=False)

# ==========================================
# MÓDULO 2: TAREFAS
# ==========================================
class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), default="em-andamento", nullable=False)
    ordem = db.Column(db.Integer, default=0, nullable=False)
    subtarefas = db.relationship('Subtarefa', backref='tarefa', lazy=True, cascade="all, delete-orphan", order_by="Subtarefa.ordem")

    @property
    def progresso(self):
        total = len(self.subtarefas)
        if total == 0:
            return 0
        concluidas = sum(1 for s in self.subtarefas if s.concluida)
        return int((concluidas / total) * 100)

class Subtarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(150), nullable=False)
    concluida = db.Column(db.Boolean, default=False)
    ordem = db.Column(db.Integer, default=0) # Para o ranqueamento
    tarefa_id = db.Column(db.Integer, db.ForeignKey('tarefa.id'), nullable=False)

# ==========================================
# MÓDULO 3: FINANCEIRO
# ==========================================
class Ativo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False)
    display = db.Column(db.String(20), nullable=False)
    peso = db.Column(db.Float, default=0.0)
    quantidade = db.Column(db.Float, default=0.0)
    ignorar = db.Column(db.Boolean, default=False)

class HistoricoAporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    aporte = db.Column(db.Float, default=0.0)
    saldo_nao_investido = db.Column(db.Float, default=0.0)
    compras = db.relationship('CompraAtivo', backref='historico', lazy=True, cascade="all, delete-orphan")

class CompraAtivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    historico_id = db.Column(db.Integer, db.ForeignKey('historico_aporte.id'), nullable=False)
    ticker = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Float, default=0.0)
    preco = db.Column(db.Float, default=0.0)
    valor = db.Column(db.Float, default=0.0)

# ==========================================
# MÓDULO 4: ALIMENTAÇÃO
# ==========================================
class RegistroAlimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, default=date.today, nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    calorias = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # 'Dieta' ou 'Extra'

class MetricasAlimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, default=date.today, unique=True, nullable=False)
    peso = db.Column(db.Float, default=0.0)
    meta_calorias = db.Column(db.Integer, default=2000)

class RefeicaoFixa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    calorias = db.Column(db.Integer, nullable=False)