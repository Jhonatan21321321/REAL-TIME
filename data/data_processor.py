import pandas as pd
from datetime import timedelta
from .zendesk_connector import fetch_tickets, fetch_user_data, fetch_user_groups

def extract_from_dict(col, key):
    """Função auxiliar para extrair valores de dicionários em colunas"""
    return col.apply(lambda x: x.get(key) if isinstance(x, dict) else None)

def process_zendesk_data(minutes_back=5):
    """Processa os dados do Zendesk e retorna um DataFrame limpo"""
    try:
        tickets = fetch_tickets(minutes_back)
        if not tickets:
            print("Nenhum ticket retornado pela API")
            return pd.DataFrame()
            
        df = pd.DataFrame(tickets)
        # Restante do processamento...
        
    except Exception as e:
        print(f"Erro no processamento de dados: {e}")
        return pd.DataFrame()
    
    # Processar dados
    if 'via' in df.columns:
        df['via_channel'] = df['via'].str.get('channel')
    if 'tags' in df.columns:
        df['tags'] = df['tags'].apply(lambda x: ', '.join(x) if isinstance(x, list) else None)
    if 'satisfaction_rating' in df.columns:
        df['satisfaction_rating'] = pd.to_numeric(df['satisfaction_rating'], errors='coerce')

    # Processar informações de usuários
    if 'assignee_id' in df.columns and not df['assignee_id'].isnull().all():
        user_ids = df['assignee_id'].dropna().unique().astype(int).tolist()
        users = fetch_user_data(user_ids)
        
        if users:
            # Mapear nomes
            id_to_name = {u['id']: u['name'] for u in users}
            df['assignee_name'] = df['assignee_id'].map(id_to_name)
            
            # Mapear grupos
            id_to_groups = {}
            id_to_last_login = {}  # Novo dicionário para last_login_at
            for user_id in user_ids:
                groups = fetch_user_groups(user_id)
                id_to_groups[user_id] = ', '.join([g['name'] for g in groups])
                
                # Adicionar last_login_at do usuário
                user = next((u for u in users if u['id'] == user_id), None)
                id_to_last_login[user_id] = user.get('last_login_at') if user else None
            
            df['assignee_groups'] = df['assignee_id'].map(id_to_groups)
            df['assignee_last_login_at'] = df['assignee_id'].map(id_to_last_login)  # Nova coluna
    
    # Ajustar fusos horários
    for col in ['created_at', 'updated_at', 'assignee_last_login_at']:  # Adicionei a nova coluna aqui
        if col in df.columns:
            df[col] = (pd.to_datetime(df[col]) - timedelta(hours=3)).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Selecionar colunas relevantes
    cols = ['id','assignee_name', 'status', 'via_channel',
            'type' , 'created_at', 'updated_at','satisfaction_rating', 'tags', 'assignee_groups', 'assignee_last_login_at']  # Adicionei a nova coluna aqui
    
    existing_cols = [c for c in cols if c in df.columns]
    return df[existing_cols] if existing_cols else pd.DataFrame()