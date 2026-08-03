import os
from models import db, Ativo

BASE_DIR = os.path.dirname(__file__)
PORTFOLIO_FILE = os.path.join(BASE_DIR, "portfolio.json")
HISTORICO_FILE = os.path.join(BASE_DIR, "historico_aportes.json")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

DEFAULT_PORTFOLIO = [
    {"ticker": "AURA33.SA", "display": "AURA33.SA", "peso": 1, "quantidade": 35},
]

def load_portfolio():
    ativos = Ativo.query.all()
    
    if not ativos:
        # Se estiver vazio, adiciona o default e recarrega
        save_portfolio(DEFAULT_PORTFOLIO)
        ativos = Ativo.query.all()
        
    portfolio = []
    for a in ativos:
        portfolio.append({
            "ticker": a.ticker,
            "display": a.display,
            "peso": a.peso,
            "quantidade": a.quantidade,
            "ignorar": a.ignorar
        })
    return portfolio

def save_portfolio(portfolio):
    # Deleta os ativos atuais
    Ativo.query.delete()
    
    # Insere a nova lista
    for item in portfolio:
        novo_ativo = Ativo(
            ticker=item["ticker"],
            display=item["display"],
            peso=item.get("peso", 0),
            quantidade=item.get("quantidade", 0),
            ignorar=item.get("ignorar", False)
        )
        db.session.add(novo_ativo)
    
    db.session.commit()

def add_ativo(ticker, display, peso, quantidade):
    if not ticker:
        raise ValueError("Ticker obrigatório")
    if peso <= 0:
        raise ValueError("Peso deve ser maior que zero")

    existe = Ativo.query.filter_by(display=display).first()
    if existe:
        raise ValueError(f"Ativo '{display}' já existe na carteira")

    novo_ativo = Ativo(
        ticker=ticker,
        display=display,
        peso=peso,
        quantidade=quantidade,
        ignorar=False
    )
    db.session.add(novo_ativo)
    db.session.commit()
    
    return load_portfolio()

def remove_ativo(display):
    ativo = Ativo.query.filter_by(display=display.upper()).first()
    if not ativo:
        raise ValueError(f"Ativo '{display}' não encontrado")
    
    db.session.delete(ativo)
    db.session.commit()
    
    return load_portfolio()

def update_ativo(display, quantidade=None, peso=None):
    ativo = Ativo.query.filter_by(display=display.upper()).first()
    if not ativo:
        raise ValueError("Ativo não encontrado")
        
    if quantidade is not None:
        ativo.quantidade = float(quantidade)
    if peso is not None:
        ativo.peso = float(peso)
        
    db.session.commit()

def listar_backups():
    return []

def restaurar_backup(arquivo):
    raise ValueError("Backups físicos desabilitados. Os dados agora estão salvos no banco de dados.")