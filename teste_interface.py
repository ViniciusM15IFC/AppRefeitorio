import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cardápio Escolar", layout="wide")

st.title("📅 Cardápio Escolar")

# Upload de arquivo
file = st.file_uploader("Carregar planilha", type=["csv", "xlsx"])

if file:
    try:
        # Carrega com Pandas
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        # Normaliza Data se existir
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.strftime("%Y-%m-%d")

        # Exibe a tabela
        st.subheader("📊 Dados carregados")
        st.dataframe(df, use_container_width=True)

        # Filtro opcional por dia
        if "Data" in df.columns:
            dias_unicos = df["Data"].dropna().unique()
            dia_escolhido = st.selectbox("Filtrar por dia", ["Todos"] + list(dias_unicos))
            if dia_escolhido != "Todos":
                df = df[df["Data"] == dia_escolhido]
                st.write(f"Mostrando cardápio para **{dia_escolhido}**")
                st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
