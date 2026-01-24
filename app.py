import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Tibia Tracker MS Cloud", layout="wide")

# URL da sua planilha
SHEET_URL = "SUA_URL_DO_GOOGLE_SHEETS_AQUI" 

# --- FUNÇÃO: CALCULAR XP TOTAL ---
def xp_for_level(level):
    return int((50/3) * (level**3 - 6*level**2 + 17*level - 12))

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(spreadsheet=SHEET_URL, ttl=0)
        # Verifica se as colunas essenciais existem, senão retorna DF vazio estruturado
        required_columns = ["Data", "Level", "Local", "Tempo (min)", "XP Total", "XP/h Real", "Lucro", "Supplies"]
        if data.empty or not set(required_columns).issubset(data.columns):
            return pd.DataFrame(columns=required_columns)
        return data
    except Exception:
        # Se der erro de conexão ou planilha vazia, retorna DF vazio para não quebrar o site
        return pd.DataFrame(columns=["Data", "Level", "Local", "Tempo (min)", "XP Total", "XP/h Real", "Lucro", "Supplies"])

# --- FUNÇÃO: PARSEAR LOG ---
def parse_log(log_text, location, current_level):
    try:
        def clean_num(label):
            pattern = rf"{label}: ([\d,.\-]+)"
            match = re.search(pattern, log_text)
            if match:
                val = match.group(1).replace(',', '').replace('.', '')
                return int(val)
            return 0

        xp_gain = clean_num('XP Gain')
        loot = clean_num('Loot')
        supplies = clean_num('Supplies')
        balance = clean_num('Balance')
        
        time_match = re.search(r'Session: (\d+):(\d+)h', log_text)
        duration_minutes = (int(time_match.group(1)) * 60) + int(time_match.group(2)) if time_match else 0
        xp_per_hour_real = (xp_gain / duration_minutes) * 60 if duration_minutes > 0 else 0

        return [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            int(current_level),
            location,
            duration_minutes,
            xp_gain,
            int(xp_per_hour_real),
            balance,
            supplies
        ]
    except Exception as e:
        st.error(f"Erro no log: {e}")
        return None

# --- INTERFACE ---
st.title("🧙‍♂️ MS Tracker Cloud")

# Carregar dados (agora blindado contra erros)
df = load_data()

# Garantir que input_level tenha um valor padrão seguro
last_level = 157
if not df.empty and "Level" in df.columns:
    try:
        last_level = int(df["Level"].max())
    except:
        pass

# Sidebar para Inputs
st.sidebar.header("📝 Nova Hunt")
input_level = st.sidebar.number_input("Level Atual", value=last_level)
input_local = st.sidebar.text_input("Local", "Lava Lurkers")
input_log = st.sidebar.text_area("Cole o Log:")

if st.sidebar.button("Enviar para Nuvem"):
    new_row = parse_log(input_log, input_local, input_level)
    if new_row:
        # Adiciona a nova linha e atualiza a planilha
        new_df = pd.DataFrame([new_row], columns=["Data", "Level", "Local", "Tempo (min)", "XP Total", "XP/h Real", "Lucro", "Supplies"])
        updated_df = pd.concat([df, new_df], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, data=updated_df)
        st.sidebar.success("Dados salvos no Google Sheets!")
        st.rerun()

# --- DASHBOARD ---
if not df.empty and "Level" in df.columns:
    xp_faltante_400 = xp_for_level(400) - xp_for_level(input_level)
    
    col1, col2 = st.columns(2)
    col1.metric("XP Total", f"{xp_for_level(input_level):,}")
    col2.metric("XP para o 400", f"{xp_faltante_400:,}")
    
    progresso = xp_for_level(input_level) / xp_for_level(400)
    st.progress(min(progresso, 1.0))
    
    st.subheader("Histórico Online")
    st.dataframe(df.sort_index(ascending=False))
else:
    st.info("Conectado! Adicione sua primeira hunt na barra lateral.")
