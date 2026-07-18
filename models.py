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

class RegistroHabito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, default=date.today, nullable=False)
    concluido = db.Column(db.Boolean, default=False)
    habito_id = db.Column(db.Integer, db.ForeignKey('habito.id'), nullable=False)

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