import json
import os
import math
import yfinance as yf
from datetime import datetime

from .storage import (
    load_portfolio,
    save_portfolio,
    PORTFOLIO_FILE,
    HISTORICO_FILE,
    BACKUP_DIR
)
def fetch_prices(portfolio):

    prices = {}

    for item in portfolio:

        symbol = formatar_ticker_yahoo(
            item["ticker"]
        )

        try:

            ticker = yf.Ticker(symbol)

            hist = ticker.history(
                period="5d"
            )

            if hist is None or hist.empty:

                prices[item["display"]] = None
                continue

            price = hist["Close"].iloc[-1]

            prices[item["display"]] = round(
                float(price),
                2
            )

        except Exception as e:

            print(
                f"Erro ao buscar {symbol}: {e}"
            )

            prices[item["display"]] = None

    return prices

def calcular_rebalanceamento(
    portfolio,
    precos,
    aporte=0,
    tolerancia=0.5
):

    ativos = []

    # --------------------------------
    # 1. Base
    # --------------------------------

    for item in portfolio:

        ticker = item["display"]

        preco = (
            precos.get(ticker, 0)
            or 0
        )

        qtd = item.get(
            "quantidade",
            0
        )

        peso_alvo = item.get(
            "peso",
            0
        )

        valor_atual = preco * qtd

        ativos.append({

            "display": ticker,

            "quantidade": qtd,

            "preco_atual": preco,

            "valor_atual": valor_atual,

            "peso_alvo": peso_alvo,

            "peso_atual": 0,

            "peso_recomendado":
                peso_alvo * 100,

            "delta_peso": 0,

            "necessidade": 0,

            "orientacao":
                "Peso aceitável",

            "css_class": "ok",

            "sugestao_qtd": 0,

            "sugestao_valor": 0,
        })

    valor_carteira = sum(
        a["valor_atual"]
        for a in ativos
    )

    valor_total = (
        valor_carteira +
        aporte
    )

    if valor_total == 0:

        valor_total = 1

    # --------------------------------
    # 2. Métricas
    # --------------------------------

    for a in ativos:

        peso_atual = (
            a["valor_atual"]
            / valor_total
        ) * 100

        peso_alvo = (
            a["peso_alvo"]
            * 100
        )

        delta = (
            peso_atual -
            peso_alvo
        )

        a["peso_atual"] = round(
            peso_atual,
            2
        )

        a["delta_peso"] = round(
            delta,
            2
        )

        a["necessidade"] = (
            a["peso_alvo"]
            * valor_total
        ) - a["valor_atual"]

        if abs(delta) <= tolerancia:

            a["orientacao"] = (
                "Peso aceitável"
            )

            a["css_class"] = "ok"

        elif delta < -tolerancia:

            a["orientacao"] = (
                "Comprar"
            )

            a["css_class"] = "buy"

        else:

            a["orientacao"] = (
                "Manter"
            )

            a["css_class"] = "sell"

    # --------------------------------
    # 3. Distribuição
    # --------------------------------

    candidatos = [

        a for a in ativos

        if a["necessidade"] > 0
        and a["preco_atual"] > 0
    ]

    soma_necessidade = sum(
        a["necessidade"]
        for a in candidatos
    ) or 1

    saldo = aporte

    for a in candidatos:

        if saldo <= 0:
            break

        fatia = (
            a["necessidade"]
            / soma_necessidade
        ) * aporte

        valor = min(
            fatia,
            saldo
        )

        qtd = int(
            valor //
            a["preco_atual"]
        )

        a["sugestao_qtd"] = qtd

        a["sugestao_valor"] = round(
            qtd *
            a["preco_atual"],
            2
        )

        saldo -= (
            qtd *
            a["preco_atual"]
        )

    # --------------------------------
    # 4. Recalcular
    # --------------------------------

    valor_investido = (
        aporte - saldo
    )

    valor_total_final = (
        valor_carteira +
        valor_investido
    )

    for a in ativos:

        qtd_final = (
            a["quantidade"] +
            a["sugestao_qtd"]
        )

        valor_final = (
            qtd_final *
            a["preco_atual"]
        )

        a["peso_atual"] = round(
            (
                valor_final /
                valor_total_final
            ) * 100
            if valor_total_final > 0
            else 0,
            2
        )

        a["delta_peso"] = round(
            a["peso_atual"]
            -
            a["peso_alvo"] * 100,
            2
        )

    # --------------------------------
    # 5. Retorno
    # --------------------------------

    return {

        "ativos": ativos,

        "valor_carteira": round(
            valor_carteira,
            2
        ),

        "valor_total": round(
            valor_total,
            2
        ),

        "aporte": aporte,

        "saldo_nao_investido":
            round(
                saldo,
                2
            ),

        "tolerancia":
            tolerancia
    }

def aplicar_rebalanceamento(data):

    ativos = data.get(
        "ativos",
        []
    )

    aporte = float(
        data.get(
            "aporte",
            0
        )
    )

    saldo = float(
        data.get(
            "saldo_nao_investido",
            0
        )
    )

    compras = [

        a for a in ativos

        if a.get(
            "sugestao_qtd",
            0
        ) > 0
    ]

    if not compras:

        raise ValueError(
            "Nenhuma compra sugerida para aplicar."
        )

    portfolio = load_portfolio()

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    backup_file = os.path.join(
        BACKUP_DIR,
        f"portfolio_{timestamp}.json"
    )

    with open(
        backup_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            portfolio,
            f,
            ensure_ascii=False,
            indent=2
        )

    historico = []

    if os.path.exists(
        HISTORICO_FILE
    ):

        try:

            with open(
                HISTORICO_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                historico = json.load(f)

        except:

            historico = []

    registro = {

        "data":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "aporte":
            aporte,

        "saldo_nao_investido":
            saldo,

        "compras": []
    }

    for compra in compras:

        ticker = compra["display"]

        for ativo in portfolio:

            if ativo["display"] == ticker:

                ativo["quantidade"] += (
                    compra[
                        "sugestao_qtd"
                    ]
                )

                registro[
                    "compras"
                ].append({

                    "ticker":
                        ticker,

                    "quantidade":
                        compra[
                            "sugestao_qtd"
                        ],

                    "preco":
                        compra[
                            "preco_atual"
                        ],

                    "valor":
                        compra[
                            "sugestao_valor"
                        ]
                })

                break

    save_portfolio(
        portfolio
    )

    historico.append(
        registro
    )

    with open(
        HISTORICO_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            historico,
            f,
            ensure_ascii=False,
            indent=2
        )

    return {
        "ok": True,
        "message":
            "Alterações aplicadas com sucesso."
    }
def formatar_ticker_yahoo(
    ticker: str
) -> str:

    ticker = ticker.upper()

    # Criptos
    if "-USD" in ticker:
        return ticker

    # Já vem formatado
    if ticker.endswith(".SA"):
        return ticker

    # Ações B3
    return f"{ticker}.SA"

def buscar_ativos(termo):
    """
    Busca ativos pelo nome ou ticker.
    """

    try:

        resultados = yf.Search(
            termo,
            max_results=15
        )

        ativos = []

        for item in resultados.quotes:

            ticker = item.get("symbol")

            nome = item.get("shortname") \
                or item.get("longname") \
                or ticker

            if ticker:

                ativos.append({
                    "ticker": ticker.replace(".SA", ""),
                    "nome": nome
                })

        return ativos

    except Exception:

        return []