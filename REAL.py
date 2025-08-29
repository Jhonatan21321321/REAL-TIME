import streamlit as st
import requests
from datetime import datetime, timedelta

# configuração
EMAIL = 'jhonatan.cruz@superbet.com'
TOKEN = 'd6FQc8anTNI0RHbn0lMvWePn03LKB87uKshEJdqi'
SUBDOMAIN = 'superbetbr'

st.set_page_config(page_title="Zendesk Tickets", layout="wide")
st.title("🎫 Tickets Abertos - Zendesk")

# selecionar intervalo em minutos
intervalo = st.slider("Intervalo em minutos:", 40, 240, 180)

# calcular timestamp
since_time = datetime.utcnow() - timedelta(minutes=intervalo) - timedelta(minutes=1)
since_timestamp = int(since_time.timestamp())

# url da API incremental
url = f"https://{SUBDOMAIN}.zendesk.com/api/v2/incremental/tickets.json?start_time={since_timestamp}&status=open"

# autenticação
auth = (f"{EMAIL}/token", TOKEN)

# requisição
try:
    resp = requests.get(url, auth=auth)
    resp.raise_for_status()
    data = resp.json()
    tickets = data.get("tickets", [])

    st.success(f"Encontrados {len(tickets)} tickets abertos nos últimos {intervalo} minutos")

    if tickets:
        for t in tickets:
            with st.expander(f"🆔 {t['id']} - {t['subject']}"):
                st.write(f"**Assunto:** {t['subject']}")
                st.write(f"**Status:** {t['status']}")
                st.write(f"**Atualizado em:** {t['updated_at']}")
                st.write(f"**Criado em:** {t['created_at']}")
                st.json(t)  # opcional: mostra todos os dados brutos

except Exception as e:
    st.error(f"Erro ao buscar tickets: {e}")
