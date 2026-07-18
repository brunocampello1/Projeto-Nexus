import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)

PORTFOLIO_FILE = os.path.join(
    BASE_DIR,
    "portfolio.json"
)

HISTORICO_FILE = os.path.join(
    BASE_DIR,
    "historico_aportes.json"
)

BACKUP_DIR = os.path.join(
    BASE_DIR,
    "backups"
)

os.makedirs(
    BACKUP_DIR,
    exist_ok=True
)

DEFAULT_PORTFOLIO = [
    {"ticker": "AURA33.SA", "display": "AURA33.SA", "peso": 1, "quantidade": 35},

]


def load_portfolio():

    if os.path.exists(PORTFOLIO_FILE):

        try:

            with open(
                PORTFOLIO_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception:
            pass

    save_portfolio(
        DEFAULT_PORTFOLIO
    )

    return DEFAULT_PORTFOLIO

def save_portfolio(portfolio):

    with open(
        PORTFOLIO_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            portfolio,
            f,
            ensure_ascii=False,
            indent=2
        )

def add_ativo(
    ticker,
    display,
    peso,
    quantidade
):

    if not ticker:

        raise ValueError(
            "Ticker obrigatório"
        )

    if peso <= 0:

        raise ValueError(
            "Peso deve ser maior que zero"
        )

    portfolio = load_portfolio()

    if any(
        a["display"] == display
        for a in portfolio
    ):

        raise ValueError(
            f"Ativo '{display}' já existe na carteira"
        )

    portfolio.append({

        "ticker": ticker,

        "display": display,

        "peso": peso,

        "quantidade": quantidade
    })

    save_portfolio(
        portfolio
    )

    return portfolio
def remove_ativo(display):

    portfolio = load_portfolio()

    nova = [

        a for a in portfolio

        if a["display"]
        != display.upper()
    ]

    if len(nova) == len(portfolio):

        raise ValueError(
            f"Ativo '{display}' não encontrado"
        )

    save_portfolio(
        nova
    )

    return nova

def update_ativo(
    display,
    quantidade=None,
    peso=None
):

    portfolio = load_portfolio()

    for ativo in portfolio:

        if ativo["display"] == display.upper():

            if quantidade is not None:

                ativo["quantidade"] = int(
                    quantidade
                )

            if peso is not None:

                ativo["peso"] = float(
                    peso
                )

            save_portfolio(
                portfolio
            )

            return

    raise ValueError(
        "Ativo não encontrado"
    )
def formatar_data_backup(nome):

    raw = (
        nome
        .replace("portfolio_", "")
        .replace(".json", "")
    )

    dt = datetime.strptime(
        raw,
        "%Y-%m-%d_%H-%M-%S"
    )

    return dt.strftime(
        "%d/%m/%Y %H:%M"
    )

def listar_backups():

    if not os.path.exists(
        BACKUP_DIR
    ):

        return []

    arquivos = []

    for nome in sorted(
        os.listdir(BACKUP_DIR),
        reverse=True
    ):

        if nome.endswith(".json"):

            arquivos.append({

                "arquivo": nome,

                "data":
                    formatar_data_backup(
                        nome
                    )
            })

    return arquivos

def restaurar_backup(arquivo):

    if not arquivo:

        raise ValueError(
            "Backup não informado."
        )

    caminho = os.path.join(
        BACKUP_DIR,
        arquivo
    )

    if not os.path.exists(
        caminho
    ):

        raise ValueError(
            "Backup não encontrado."
        )

    with open(
        caminho,
        "r",
        encoding="utf-8"
    ) as f:

        carteira = json.load(f)

    save_portfolio(
        carteira
    )

    return {

        "ok": True,

        "message":
            "Carteira restaurada com sucesso."
    }