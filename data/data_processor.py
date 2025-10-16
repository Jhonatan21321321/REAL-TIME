import pandas as pd
from datetime import timedelta
import re
from .zendesk_connector import fetch_tickets, fetch_user_data, fetch_user_groups

# Regex para bater exatamente com as tags de sentimento
SENTIMENT_PATTERN = re.compile(
    r'^sentiment__(very_positive|positive|neutral|negative|very_negative)$',
    re.IGNORECASE
)

def extract_sentiment_from_tags(tags):
    """
    Retorna 'very positive' | 'positive' | 'neutral' | 'negative' | 'very negative'
    ou None se não houver tag 'sentiment__...'.
    """
    if not isinstance(tags, list):
        return None
    for t in tags:
        if not isinstance(t, str):
            continue
        m = SENTIMENT_PATTERN.match(t.strip().lower())
        if m:
            return m.group(1).replace('_', ' ')
    return None  # Não encontrou nenhuma tag de sentimento -> nulo

def process_zendesk_data(minutes_back=5):
    try:
        tickets = fetch_tickets(minutes_back)
        if not tickets:
            print("Nenhum ticket retornado pela API")
            return pd.DataFrame()
        df = pd.DataFrame(tickets)
    except Exception as e:
        print(f"Erro no processamento de dados: {e}")
        return pd.DataFrame()
    
    # via_channel
    if 'via' in df.columns:
        df['via_channel'] = df['via'].str.get('channel')

    # sentiment_5 somente a partir das tags; se não houver, fica None
    if 'tags' in df.columns:
        df['sentiment_5'] = df['tags'].apply(extract_sentiment_from_tags)
        # opcional: manter tags como string para exibição
        df['tags'] = df['tags'].apply(lambda x: ', '.join(x) if isinstance(x, list) else None)
    else:
        df['sentiment_5'] = None

    # satisfaction_rating numérico
    if 'satisfaction_rating' in df.columns:
        df['satisfaction_rating'] = pd.to_numeric(df['satisfaction_rating'], errors='coerce')

    # sem fallback de outras colunas sentiment*
    # sem default para "neutral"

    # Dados de usuários
    if 'assignee_id' in df.columns and not df['assignee_id'].isnull().all():
        user_ids = df['assignee_id'].dropna().unique().astype(int).tolist()
        users = fetch_user_data(user_ids)
        if users:
            id_to_name = {u['id']: u['name'] for u in users}
            df['assignee_name'] = df['assignee_id'].map(id_to_name)
            id_to_groups, id_to_last_login = {}, {}
            for user_id in user_ids:
                groups = fetch_user_groups(user_id)
                id_to_groups[user_id] = ', '.join([g['name'] for g in groups])
                user = next((u for u in users if u['id'] == user_id), None)
                id_to_last_login[user_id] = user.get('last_login_at') if user else None
            df['assignee_groups'] = df['assignee_id'].map(id_to_groups)
            df['assignee_last_login_at'] = df['assignee_id'].map(id_to_last_login)
    
    # Fuso horário
    for col in ['created_at', 'updated_at', 'assignee_last_login_at']:
        if col in df.columns:
            df[col] = (pd.to_datetime(df[col], errors='coerce') - timedelta(hours=3)).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Seleção de colunas
    cols = [
        'id', 'assignee_name', 'status', 'via_channel',
        'type', 'created_at', 'updated_at', 'satisfaction_rating', 'sentiment_5',
        'tags', 'assignee_groups', 'assignee_last_login_at'
    ]
    existing_cols = [c for c in cols if c in df.columns]
    return df[existing_cols] if existing_cols else pd.DataFrame()
