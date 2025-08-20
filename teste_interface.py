import streamlit as st
import pandas as pd
import calendar

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

        # Normaliza a coluna Data
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

        # Exibe preview
        st.subheader("📊 Dados carregados")
        st.dataframe(df, use_container_width=True)

        if "Data" in df.columns:
            # Pega ano e mês (assumindo que todos os dias são do mesmo mês)
            ano = df["Data"].dt.year.mode()[0]
            mes = df["Data"].dt.month.mode()[0]

            st.markdown(f"### 📅 Calendário de {calendar.month_name[mes]} {ano}")

            # Gerar calendário
            cal = calendar.monthcalendar(ano, mes)

            for semana in cal:
                cols = st.columns(7)
                for i, dia in enumerate(semana):
                    if dia == 0:
                        cols[i].markdown(" ")
                    else:
                        data_dia = pd.Timestamp(year=ano, month=mes, day=dia)
                        if data_dia in df["Data"].values:
                            if cols[i].button(str(dia), key=f"{ano}-{mes}-{dia}"):
                                with st.modal(f"🍽 Cardápio - {data_dia.strftime('%d/%m/%Y')}"):
                                    df_dia = df[df["Data"] == data_dia]
                                    st.table(df_dia)
                        else:
                            cols[i].markdown(f"**{dia}**")

    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
