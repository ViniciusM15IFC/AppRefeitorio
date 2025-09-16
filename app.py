from flask import Flask, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import requests
from io import StringIO

app = Flask(__name__)
CORS(app)

SHEET_ID = '1HTAu3tJUjXcX_CaVgFL6wRCt1jrI5Eq-7YiCcTVcgng'

def listar_meses():
    """
    Lê a aba 'Meses' da planilha pública e retorna lista de dicionários com id e nome.
    """
    try:
        # URL correta para acessar a aba 'Meses' como CSV
        url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Meses'
        
        # Fazendo requisição e convertendo para DataFrame
        response = requests.get(url)
        response.raise_for_status()
        
        # Lendo o CSV
        df = pd.read_csv(StringIO(response.text))
        
        # Remove linhas vazias
        df = df.dropna()
        
        # Cria lista de dicionários com id e nome
        meses = []
        for _, row in df.iterrows():
            if len(row) >= 2 and pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                meses.append({
                    'id': str(row.iloc[0]).strip(),  # Primeira coluna (ID: 202509)
                    'nome': str(row.iloc[1]).strip()  # Segunda coluna (Nome: Setembro de 2025)
                })
        
        return meses
    except Exception as e:
        print("Erro ao listar meses:", e)
        return []

def carregar_cardapio(sheet_name):
    """
    Lê CSV público da aba e retorna lista de dicionários
    """
    try:
        sheet_name_encoded = sheet_name.replace(' ', '%20')
        url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name_encoded}'
        
        response = requests.get(url)
        response.raise_for_status()
        
        df = pd.read_csv(StringIO(response.text))
        return df.to_dict('records')
    except Exception as e:
        print(f"Erro ao carregar cardápio {sheet_name}:", e)
        return {"erro": str(e)}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/cardapio/<mes>", methods=["GET"])
def get_cardapio(mes):
    dados = carregar_cardapio(mes)
    return jsonify(dados)

@app.route("/api/meses", methods=["GET"])
def get_meses():
    meses = listar_meses()
    return jsonify(meses)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)