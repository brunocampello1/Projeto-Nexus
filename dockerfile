# 1. Usa uma imagem oficial do Python, versão slim (mais leve e rápida)
FROM python:3.11-slim

# 2. Define a pasta de trabalho dentro do contêiner
WORKDIR /app

# 3. Copia apenas o arquivo de dependências primeiro (isso otimiza o cache do Docker)
COPY requirements.txt .

# 4. Instala as dependências listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia todo o restante do código da sua máquina para o contêiner
COPY . .

# 6. Informa qual porta a aplicação vai usar (5000 é o padrão do Flask)
EXPOSE 5000

# 7. Comando para rodar a aplicação em produção usando Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]