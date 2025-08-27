import streamlit as st
import pandas as pd
import calendar
import locale
from datetime import datetime
import re

# Configurar locale para português (se disponível)
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except:
        pass  # Usar inglês como fallback

# Configurar calendário para começar na segunda-feira
calendar.setfirstweekday(calendar.MONDAY)

st.set_page_config(page_title="Cardápio Escolar", layout="wide")

# CSS customizado para destacar texto e botões
st.markdown("""
<style>
.highlighted-text {
    background-color: #1f77b4;
    color: white;
    padding: 2px 4px;
    border-radius: 3px;
    font-weight: bold;
}

/* Estilo para botões destacados - usando atributo data */
button[data-highlighted="true"] {
    background-color: #1976d2 !important;
    color: white !important;
    border: 2px solid #0d47a1 !important;
    box-shadow: 0 4px 8px rgba(25, 118, 210, 0.3) !important;
}

/* Alternativa usando classes */
.highlighted-button button {
    background-color: #1976d2 !important;
    color: white !important;
    border: 2px solid #0d47a1 !important;
    box-shadow: 0 4px 8px rgba(25, 118, 210, 0.3) !important;
}
</style>
""", unsafe_allow_html=True)

st.title("📅 Cardápio Escolar")

def parse_portuguese_date(date_str):
    """Converte data em português para datetime"""
    if pd.isna(date_str) or not isinstance(date_str, str):
        return None
    
    # Mapeamento de meses em português
    meses = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }
    
    try:
        # Remove quebras de linha e espaços extras
        date_str = re.sub(r'\s+', ' ', date_str.strip())
        
        # Padrão: "dia-da-semana, DD de mês de AAAA"
        pattern = r'.*?(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
        match = re.search(pattern, date_str.lower())
        
        if match:
            dia = int(match.group(1))
            mes_nome = match.group(2)
            ano = int(match.group(3))
            
            if mes_nome in meses:
                mes = meses[mes_nome]
                return datetime(ano, mes, dia)
    except:
        pass
    
    return None

def search_in_menu(row, search_term):
    """Verifica se o termo de busca está presente em qualquer categoria do cardápio"""
    if not search_term:
        return False
    
    search_term = search_term.lower()
    categorias = ['Acompanhamento', 'Guarnição', 'Prato Principal', 'Saladas', 'Vegetariano']
    
    for categoria in categorias:
        if categoria in row and pd.notna(row[categoria]):
            if search_term in str(row[categoria]).lower():
                return True
    return False

def highlight_search_term(text, search_term):
    """Destaca o termo pesquisado no texto com HTML"""
    if not search_term or not text:
        return text
    
    # Escapa caracteres especiais do regex
    escaped_term = re.escape(search_term)
    
    # Substitui o termo encontrado por uma versão destacada
    highlighted = re.sub(
        f'({escaped_term})', 
        r'<span class="highlighted-text">\1</span>', 
        str(text), 
        flags=re.IGNORECASE
    )
    
    return highlighted

# Upload de arquivo
file = st.file_uploader("Carregar planilha", type=["csv", "xlsx"])

if file:
    try:
        # Carrega com Pandas
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        # Exibe preview dos dados carregados
        st.subheader("📊 Dados carregados")
        st.dataframe(df, use_container_width=True)
        
        # Mostra as colunas disponíveis para debug
        st.write("**Colunas disponíveis:**", list(df.columns))
        
        # Procura por colunas que podem conter datas
        possible_date_columns = []
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['data', 'dia', 'date']):
                possible_date_columns.append(col)
        
        if possible_date_columns:
            # Se encontrou colunas possíveis, permite ao usuário escolher
            date_column = st.selectbox("Selecione a coluna de data:", possible_date_columns)
            
            # Converte as datas em português
            st.info("Convertendo datas em português...")
            df['Data_Convertida'] = df[date_column].apply(parse_portuguese_date)
            
            # Remove linhas com datas inválidas
            df_valid = df.dropna(subset=['Data_Convertida'])
            
            # Mostra algumas conversões para debug
            st.write("**Exemplos de conversão:**")
            sample_data = df[[date_column, 'Data_Convertida']].head()
            st.dataframe(sample_data)
            
            if not df_valid.empty:
                # Pega ano e mês (assumindo que todos os dias são do mesmo mês)
                ano = df_valid['Data_Convertida'].dt.year.mode()[0]
                mes = df_valid['Data_Convertida'].dt.month.mode()[0]

                # Nomes dos meses em português
                meses_pt = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                           'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

                st.markdown(f"### 📅 Calendário de {meses_pt[mes]} {ano}")
                
                # Barra de pesquisa com busca em tempo real
                st.markdown("---")
                
                # Inicializa o estado da sessão se não existir
                if 'search_term' not in st.session_state:
                    st.session_state.search_term = ""
                
                # Campo de busca que atualiza em tempo real
                search_term = st.text_input(
                    "🔍 Pesquisar comida no cardápio:", 
                    value=st.session_state.search_term,
                    placeholder="Ex: frango, arroz, salada...",
                    key="search_input"
                )
                
                # Atualiza o estado da sessão
                st.session_state.search_term = search_term
                
                # Se há termo de busca, encontrar dias correspondentes
                highlighted_days = set()
                if search_term:
                    for _, row in df_valid.iterrows():
                        if search_in_menu(row, search_term):
                            highlighted_days.add(row['Data_Convertida'].day)
                    
                    if highlighted_days:
                        st.success(f"🎯 Encontrados {len(highlighted_days)} dias com '{search_term}' no cardápio!")
                    else:
                        st.warning(f"❌ Nenhum dia encontrado com '{search_term}' no cardápio.")
                
                st.markdown("---")

                # Gerar calendário (começando na segunda-feira)
                cal = calendar.monthcalendar(ano, mes)
                
                # Cabeçalho dos dias da semana (começando na segunda-feira)
                dias_semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
                cols_header = st.columns(7)
                for i, dia_nome in enumerate(dias_semana):
                    cols_header[i].markdown(f"**{dia_nome}**")

                for semana in cal:
                    cols = st.columns(7)
                    for i, dia in enumerate(semana):
                        if dia == 0:
                            cols[i].markdown(" ")
                        else:
                            data_dia = datetime(year=ano, month=mes, day=dia)
                            if data_dia.date() in df_valid['Data_Convertida'].dt.date.values:
                                # Verifica se o dia está destacado pela pesquisa
                                is_highlighted = dia in highlighted_days
                                
                                # Define o ícone e estilo do botão baseado na pesquisa
                                if is_highlighted:
                                    # Dia destacado com busca - aplica classe CSS
                                    with cols[i]:
                                        st.markdown('<div class="highlighted-button">', unsafe_allow_html=True)
                                        button_clicked = st.button(f"🔍 {dia}", key=f"btn_{dia}", use_container_width=True)
                                        st.markdown('</div>', unsafe_allow_html=True)
                                else:
                                    # Dia normal com cardápio
                                    button_clicked = cols[i].button(f"🍽️ {dia}", key=f"btn_{dia}", use_container_width=True)
                                
                                # Se o botão foi clicado, mostrar o cardápio diretamente
                                if button_clicked:
                                    # Encontra o cardápio do dia
                                    df_dia = df_valid[df_valid['Data_Convertida'].dt.date == data_dia.date()]
                                    
                                    # Mostra o cardápio diretamente na sidebar ou em uma nova seção
                                    st.sidebar.markdown(f"### 🍽 Cardápio - {data_dia.strftime('%d/%m/%Y')}")
                                    
                                    for _, row in df_dia.iterrows():
                                        st.sidebar.markdown(f"**📅 {row[date_column]}**")
                                        st.sidebar.markdown("---")
                                        
                                        # Mostra cada categoria do cardápio
                                        categorias = ['Acompanhamento', 'Guarnição', 'Prato Principal', 
                                                    'Saladas', 'Vegetariano']
                                        
                                        for categoria in categorias:
                                            if categoria in row and pd.notna(row[categoria]) and row[categoria].strip():
                                                content = str(row[categoria])
                                                
                                                # Destaca o termo pesquisado no conteúdo
                                                if search_term and search_term.lower() in content.lower():
                                                    highlighted_content = highlight_search_term(content, search_term)
                                                    st.sidebar.markdown(f"**{categoria}:**")
                                                    st.sidebar.markdown(highlighted_content, unsafe_allow_html=True)
                                                else:
                                                    st.sidebar.markdown(f"**{categoria}:**")
                                                    st.sidebar.markdown(f"{content}")
                                            st.sidebar.markdown("")
                            else:
                                # Dia sem cardápio
                                cols[i].markdown(f"**{dia}**")
                
                # Legenda
                if search_term:
                    st.markdown("---")
                    st.markdown("**Legenda:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("🔍 - Dias com o termo pesquisado")
                    with col2:
                        st.markdown("🍽️ - Dias com cardápio")
                        
            else:
                st.warning("Não foi possível converter as datas. Verifique o formato da coluna selecionada.")
                st.write("Formato esperado: 'segunda-feira, 2 de junho de 2025'")
        else:
            st.warning("Não foi encontrada nenhuma coluna que pareça conter datas. As colunas devem conter 'data', 'dia' ou 'date' no nome.")

    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        st.write("**Debug info:**")
        st.write(f"Tipo do erro: {type(e).__name__}")
        st.write(f"Detalhes: {str(e)}")
