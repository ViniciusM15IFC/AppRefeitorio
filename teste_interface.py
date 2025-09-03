import streamlit as st
import pandas as pd
import calendar
import locale
from datetime import datetime
import re
import os

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

# CSS customizado para destacar texto, botões e responsividade
st.markdown("""
<style>
.highlighted-text {
    background-color: #1f77b4;
    color: white;
    padding: 2px 4px;
    border-radius: 3px;
    font-weight: bold;
}

/* Estilo para botões destacados */
.highlighted-button button {
    background-color: #1976d2 !important;
    color: white !important;
    border: 2px solid #0d47a1 !important;
    box-shadow: 0 4px 8px rgba(25, 118, 210, 0.3) !important;
}

/* Estilo responsivo para o calendário */
@media (max-width: 768px) {
    .stColumns {
        gap: 0.2rem !important;
    }
    
    .stButton button {
        font-size: 0.8rem !important;
        padding: 0.3rem !important;
        min-height: 2.5rem !important;
    }
    
    .calendar-header {
        font-size: 0.9rem !important;
        text-align: center !important;
    }
}

@media (min-width: 769px) {
    .stButton button {
        font-size: 1rem !important;
        padding: 0.5rem !important;
        min-height: 3rem !important;
    }
    
    .calendar-header {
        font-size: 1.1rem !important;
        text-align: center !important;
    }
}

/* Estilo para categorias no modal - sem caixas brancas */
.categoria-item {
    padding: 15px 0;
    margin-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.categoria-item:last-child {
    border-bottom: none;
}

.categoria-titulo {
    color: #1976d2;
    font-weight: bold;
    font-size: 1.2em;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.categoria-conteudo {
    color: #ffffff;
    font-size: 1em;
    line-height: 1.4;
    margin-left: 32px;
}

/* Responsividade para mobile no modal */
@media (max-width: 768px) {
    .categoria-titulo {
        font-size: 1.1em;
    }
    
    .categoria-conteudo {
        font-size: 0.95em;
        margin-left: 28px;
    }
    
    .categoria-item {
        padding: 12px 0;
        margin-bottom: 12px;
    }
}

/* Estilo para o cabeçalho do calendário */
.calendar-header {
    font-weight: bold;
    text-align: center;
    padding: 0.5rem 0;
    background-color: rgba(25, 118, 210, 0.1);
    border-radius: 5px;
    margin-bottom: 0.5rem;
}

/* Ajustes para botões do calendário */
.stButton button {
    width: 100% !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}

.stButton button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
}

/* Estilo para dias sem cardápio */
.day-no-menu {
    text-align: center;
    padding: 0.5rem;
    color: #666;
    font-weight: normal;
}

@media (max-width: 768px) {
    .day-no-menu {
        font-size: 0.9rem;
        padding: 0.3rem;
    }
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

@st.dialog("🍽️ Cardápio do Dia")
def show_cardapio_modal(df_dia, date_column, data_dia, search_term=""):
    """Mostra o cardápio do dia em um modal"""
    
    # Formatação da data em português
    try:
        data_formatada = data_dia.strftime('%A, %d de %B de %Y')
    except:
        data_formatada = data_dia.strftime('%d/%m/%Y')
    
    st.markdown(f"### 📅 {data_formatada}")
    st.markdown("---")
    
    for _, row in df_dia.iterrows():
        # Mostra cada categoria do cardápio sem caixas brancas
        categorias = ['Acompanhamento', 'Guarnição', 'Prato Principal', 
                    'Saladas', 'Vegetariano']
        
        # Ícones para cada categoria
        categoria_icons = {
            'Acompanhamento': '🍚',
            'Guarnição': '🥕',
            'Prato Principal': '🍖',
            'Saladas': '🥗',
            'Vegetariano': '🌱'
        }
        
        for categoria in categorias:
            if categoria in row and pd.notna(row[categoria]) and str(row[categoria]).strip():
                content = str(row[categoria])
                icon = categoria_icons.get(categoria, '🍽️')
                
                # Container para cada categoria sem caixa branca
                st.markdown('<div class="categoria-item">', unsafe_allow_html=True)
                
                # Título da categoria
                st.markdown(f'<div class="categoria-titulo">{icon} {categoria}</div>', unsafe_allow_html=True)
                
                # Conteúdo da categoria
                if search_term and search_term.lower() in content.lower():
                    highlighted_content = highlight_search_term(content, search_term)
                    st.markdown(f'<div class="categoria-conteudo">{highlighted_content}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="categoria-conteudo">{content}</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    # Botão para fechar o modal
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("✖️ Fechar", use_container_width=True):
            st.rerun()

# Carregamento automático do arquivo
def load_cardapio_from_public_sheets():
    """Carrega dados de planilha pública SEM cache"""
    
    try:
        sheet_id = "1P5JxySWEiHc53ixBU7HP1LJ5VVLQczzo"  # Substitua pelo ID real
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        df = pd.read_csv(csv_url)
        return df, None
        
    except Exception as e:
        return None, f"Erro ao carregar da planilha pública: {str(e)}"

# Carrega os dados automaticamente
df, error_message = load_cardapio_from_public_sheets()

if error_message:
    st.error(error_message)
    st.info("Certifique-se de que o arquivo 'cardapio_processado.csv' está no diretório raiz do projeto.")
else:
    st.success("✅ Cardápio carregado automaticamente!")
    
    # Exibe preview dos dados carregados
    with st.expander("📊 Ver dados carregados", expanded=False):
        st.dataframe(df, use_container_width=True)
        st.write("**Colunas disponíveis:**", list(df.columns))
    
    # Procura por colunas que podem conter datas
    possible_date_columns = []
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['data', 'dia', 'date']):
            possible_date_columns.append(col)
    
    if possible_date_columns:
        # Se encontrou colunas possíveis, permite ao usuário escolher ou usa a primeira automaticamente
        if len(possible_date_columns) == 1:
            date_column = possible_date_columns[0]
            st.info(f"📅 Usando coluna de data: **{date_column}**")
        else:
            date_column = st.selectbox("Selecione a coluna de data:", possible_date_columns)
        
        # Converte as datas em português
        with st.spinner("Convertendo datas em português..."):
            df['Data_Convertida'] = df[date_column].apply(parse_portuguese_date)
        
        # Remove linhas com datas inválidas
        df_valid = df.dropna(subset=['Data_Convertida'])
        
        # Mostra algumas conversões para debug (opcional)
        with st.expander("🔍 Ver exemplos de conversão de data", expanded=False):
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
                            
                            # Se o botão foi clicado, mostrar o cardápio em um modal
                            if button_clicked:
                                # Encontra o cardápio do dia
                                df_dia = df_valid[df_valid['Data_Convertida'].dt.date == data_dia.date()]
                                
                                # Mostra o cardápio em um modal
                                show_cardapio_modal(df_dia, date_column, data_dia, search_term)
                        
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

