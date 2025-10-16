import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime
from pytz import timezone
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.data_processor import process_zendesk_data
import duckdb

# Configuração da página
st.set_page_config(page_title="Superbet Zendesk Dashboard", layout="wide")

# Variável de estado para controlar a última atualização
if 'last_update' not in st.session_state:
    st.session_state.last_update = "Nunca"

@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_data(minutes_back=5):
    """Carrega e retorna os dados processados"""
    df = process_zendesk_data(minutes_back)
    
    # Converter created_at e updated_at para datetime
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    if 'updated_at' in df.columns:
        df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')
    
    return df

def calculate_time_differences(df):
    """Calcula os tempos desde criação e atualização em tempo real (HH:MM:SS e -3h)"""
    df = df.copy()
    saopaulo_tz = timezone('America/Sao_Paulo')
    now_sp = datetime.now(saopaulo_tz)

    def format_timedelta(td):
        # Remove 3 horas do timedelta
        td = td - pd.Timedelta(hours=3)
        # Se negativo, retorna 00:00:00
        if td.total_seconds() < 0:
            return "00:00:00"
        # Formata para HH:MM:SS
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    if 'created_at' in df.columns:
        df['tempo_desde_criacao'] = df['created_at'].dt.tz_localize('UTC').dt.tz_convert(saopaulo_tz)
        df['tempo_desde_criacao'] = df['tempo_desde_criacao'].apply(
            lambda x: format_timedelta(now_sp - x) if pd.notnull(x) else 'N/A'
        )

    if 'updated_at' in df.columns:
        df['tempo_desde_atualizacao'] = df['updated_at'].dt.tz_localize('UTC').dt.tz_convert(saopaulo_tz)
        df['tempo_desde_atualizacao'] = df['tempo_desde_atualizacao'].apply(
            lambda x: format_timedelta(now_sp - x) if pd.notnull(x) else 'N/A'
        )

    return df

def apply_filters(df, status_filter, via_channel_filter, assignee_groups_filter,
                  satisfaction_filter, sentiment_filter, type_filter):
    filtered_df = df.copy()
    
    if status_filter:
        filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
    if via_channel_filter:
        filtered_df = filtered_df[filtered_df['via_channel'].isin(via_channel_filter)]
    if assignee_groups_filter:
        filtered_df = filtered_df[filtered_df['assignee_groups'].isin(assignee_groups_filter)]
    if satisfaction_filter:
        filtered_df = filtered_df[filtered_df['satisfaction_rating'].isin(satisfaction_filter)]
    if sentiment_filter:
        filtered_df = filtered_df[filtered_df['sentiment_5'].isin(sentiment_filter)]
    if type_filter:
        filtered_df = filtered_df[filtered_df['type'].isin(type_filter)]
    
    return filtered_df

def main():
    st.title("Superbet Zendesk Dashboard")
    
    # Controles de atualização na sidebar
    st.sidebar.header("Atualização")
    
    minutes_back = st.sidebar.number_input(
        "Período em minutos", 
        min_value=1, 
        max_value=1440,  # 24 horas
        value=5,
        help="Define quantos minutos para trás os tickets serão buscados"
    )

    df = load_data(minutes_back)
        
    # Botão de atualização
    if st.sidebar.button("Atualizar Dados"):
        st.cache_data.clear()
        st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
        st.rerun()
    
    st.sidebar.markdown(f"**Última atualização:** {st.session_state.last_update}")
    
    # Calcular diferenças de tempo em tempo real
    df = calculate_time_differences(df)
    
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return
    
    required_columns = ['status', 'via_channel', 'assignee_groups', 'updated_at']
    for col in required_columns:
        if col not in df.columns:
            st.error(f"Coluna '{col}' não encontrada nos dados. Verifique sua fonte de dados.")
            return
    
    # Filtros adicionais na sidebar
    st.sidebar.header("Filtros")
    
    status_options = df['status'].dropna().unique().tolist()
    selected_status = st.sidebar.multiselect(
        "Status",
        options=status_options
    )
    
    via_channel_options = df['via_channel'].dropna().unique().tolist()
    selected_via_channel = st.sidebar.multiselect(
        "via_channel",
        options=via_channel_options
    )
    
    assignee_groups_options = df['assignee_groups'].dropna().unique().tolist()
    selected_assignee_groups = st.sidebar.multiselect(
        "assignee_groups",
        options=assignee_groups_options
    )
    
    if 'satisfaction_rating' in df.columns:
        satisfaction_options = df['satisfaction_rating'].dropna().unique().tolist()
        selected_satisfaction = st.sidebar.multiselect(
            "Satisfaction Rating",
            options=satisfaction_options
        )
    else:
        selected_satisfaction = []
        st.sidebar.info("Coluna 'satisfaction_rating' não encontrada")

    if 'sentiment_5' in df.columns:
        sentiment_options = df['sentiment_5'].dropna().unique().tolist()
        selected_sentiment = st.sidebar.multiselect(
            "Sentiment",
            options=sentiment_options
        )
    else:
        selected_sentiment = []
        st.sidebar.info("Coluna 'sentiment_5' não encontrada")

    if 'type' in df.columns:
        type_options = df['type'].dropna().unique().tolist()
        selected_type = st.sidebar.multiselect(
            "Type",
            options=type_options
        )
    else:
        selected_type = []
        st.sidebar.info("Coluna 'type' não encontrada")

    filtered_df = apply_filters(
        df,
        selected_status,
        selected_via_channel,
        selected_assignee_groups,
        selected_satisfaction,
        selected_sentiment,
        selected_type
    )
    
    # Reorganizar colunas para mostrar tempo_desde_* ao lado de assignee_name
    cols = filtered_df.columns.tolist()
    if 'assignee_name' in filtered_df.columns:
        cols = filtered_df.columns.tolist()
        assignee_idx = cols.index('assignee_name')
        
        time_cols = ['tempo_desde_criacao', 'tempo_desde_atualizacao']
        for c in time_cols:
            if c in cols:
                cols.remove(c)
                cols.insert(assignee_idx + 1, c)
                assignee_idx += 1
        
        filtered_df = filtered_df[cols]
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total de Tickets", len(filtered_df))
    with col2:
        open_tickets = len(filtered_df[filtered_df['status'] == 'open'])
        st.metric("Tickets Abertos", open_tickets)
    with col3:
        solved_tickets = len(filtered_df[filtered_df['status'] == 'solved'])
        st.metric("Tickets Resolvidos", solved_tickets)
    with col4:
        pending_tickets = len(filtered_df[filtered_df['status'] == 'pending'])
        st.metric("Tickets pending", pending_tickets)
    with col5:
        hold_tickets = len(filtered_df[filtered_df['status'] == 'hold']) if 'hold' in filtered_df['status'].unique() else 0
        st.metric("Tickets hold", hold_tickets)
    with col6:
        closed_tickets = len(filtered_df[filtered_df['status'] == 'closed'])
        st.metric("Tickets closed", closed_tickets)
    
    st.subheader("Tickets Filtrados")
    table_placeholder = st.empty()
    
    st.subheader("Análise por Agentes Ativos")
    with duckdb.connect(':memory:') as conn:
        conn.register('filtered_df', filtered_df)
        resultado = conn.execute("""
            SELECT
                DATEDIFF('hour', STRPTIME(MAX(assignee_last_login_at), '%Y-%m-%d %H:%M:%S'), CURRENT_TIMESTAMP) AS horas_trabalhadas,
                assignee_name, 
                status,
                COUNT(*) AS total
            FROM filtered_df
            GROUP BY assignee_name, status
        """).fetchdf()
        st.dataframe(resultado, use_container_width=True)
        
    st.subheader("Análise por Channel")
    with duckdb.connect(':memory:') as conn:
        conn.register('filtered_df', filtered_df)
        resultado = conn.execute("""
            SELECT
                via_channel,
                status,
                COUNT(*) AS total
            FROM filtered_df
            GROUP BY via_channel, status
            ORDER BY via_channel
        """).fetchdf()
        st.dataframe(resultado, use_container_width=True)
        
    st.subheader("Análise por Group")
    with duckdb.connect(':memory:') as conn:
        conn.register('filtered_df', filtered_df)
        resultado = conn.execute("""
            SELECT
                CASE 
                    WHEN assignee_groups LIKE '%T1%' THEN 'T1'
                    WHEN assignee_groups LIKE '%T2%' THEN 'T2'
                    ELSE 'OTHER'
                END AS grp,
                status,
                COUNT(*) AS total
            FROM filtered_df
            GROUP BY grp, status
            ORDER BY grp
        """).fetchdf()
        st.dataframe(resultado, use_container_width=True)
        
    # Atualizar a tabela em "tempo real"
    while True:
        updated_df = calculate_time_differences(filtered_df)
        if 'assignee_name' in updated_df.columns:
            updated_df = updated_df[cols]
        table_placeholder.dataframe(updated_df, use_container_width=True)
        time.sleep(1)

if __name__ == "__main__":
    main()
