import requests
from datetime import datetime, timedelta
from config import AUTH, BASE_URL

def fetch_tickets(minutes_back=0):
    """Busca tickets com offset automático de 180 minutos"""
    try:
        now = datetime.utcnow()
         
        # Ajuste automático: adiciona 180 minutos ao valor recebido
        start_time = now - timedelta(minutes=minutes_back )
        
        # DEBUG - verifique no terminal
        print(f"⏰ Horário REAL da busca: {start_time} (UTC)")
        print(f"📊 Minutos solicitados pelo usuário: {minutes_back}")
        print(f"🔧 Offset aplicado: 180 minutos")
        
        start_timestamp = int(start_time.timestamp())
        
        response = requests.get(
            f"{BASE_URL}/incremental/tickets.json?start_time={start_timestamp}",
            auth=AUTH,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('tickets', [])
    except Exception as e:
        print(f"❌ Erro ao buscar tickets: {e}")
        return []

def fetch_user_data(user_ids):
    """Busca dados de usuários específicos"""
    if not user_ids:
        return []
    
    try:
        response = requests.get(
            f"{BASE_URL}/users/show_many.json?ids={','.join(map(str, user_ids))}",
            auth=AUTH,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('users', [])
    except Exception as e:
        print(f"❌ Erro ao buscar dados de usuários: {e}")
        return []

def fetch_user_groups(user_id):
    """Busca grupos de um usuário específico"""
    try:
        response = requests.get(
            f"{BASE_URL}/users/{user_id}/groups.json",
            auth=AUTH,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('groups', [])
    except Exception as e:
        print(f"❌ Erro ao buscar grupos do usuário {user_id}: {e}")
        return []
