from flask import Flask, render_template

from modules.financeiro.routes import financeiro_bp

# futuros módulos
# from modules.produtividade.routes import produtividade_bp
# from modules.projetos.routes import projetos_bp

app = Flask(__name__)

# ==========================
# BLUEPRINTS
# ==========================

app.register_blueprint(
    financeiro_bp,
    url_prefix="/financeiro"
)

# app.register_blueprint(
#     produtividade_bp,
#     url_prefix="/produtividade"
# )

# app.register_blueprint(
#     projetos_bp,
#     url_prefix="/projetos"
# )

# ==========================
# HOME
# ==========================

@app.route("/")
def home():

    return render_template(
        "layout.html"
    )

# ==========================
# START
# ==========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )