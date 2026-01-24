import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Tibia Tracker MS Cloud", layout="wide")

# URL da sua planilha (substitua pela sua após criar)
SHEET_URL = "https://docs.google.com/spreadsheets/d/12vyHyK2hY_kZnHXGYYcqAQOINb_RRB-ibsVF3-E-s3I/edit?usp=sharing"

# --- FUNÇÃO: CALCULAR XP TOTAL ---
def xp_for_level(level):
    return int((50/3) * (level**3 - 6*level**2 + 17*level - 12))

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=SHEET_URL, ttl="0") # ttl=0 evita cache para ver dados na hora

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

# Carregar dados existentes
df = load_data()

# Sidebar para Inputs
st.sidebar.header("📝 Nova Hunt")
input_level = st.sidebar.number_input("Level Atual", value=int(df["Level"].max()) if not df.empty else 157)
input_local = st.sidebar.text_input("Local", "Lava Lurkers")
input_log = st.sidebar.text_area("Cole o Log:")

if st.sidebar.button("Enviar para Nuvem"):
    new_row = parse_log(input_log, input_local, input_level)
    if new_row:
        # Adiciona a nova linha ao DataFrame e atualiza a planilha
        updated_df = pd.concat([df, pd.DataFrame([new_row], columns=df.columns)], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, data=updated_df)
        st.sidebar.success("Dados salvos no Google Sheets!")
        st.rerun()

# --- DASHBOARD (Mesma lógica anterior, mas usando o df da nuvem) ---
if not df.empty:
    xp_faltante_400 = xp_for_level(400) - xp_for_level(input_level)
    
    col1, col2 = st.columns(2)
    col1.metric("XP Total", f"{xp_for_level(input_level):,}")
    col2.metric("XP para o 400", f"{xp_faltante_400:,}")
    
    st.progress(xp_for_level(input_level) / xp_for_level(400))
    
    st.subheader("Histórico Online")
    st.dataframe(df.sort_index(ascending=False))
else:
    st.info("Conectado ao Google Sheets. Adicione sua primeira hunt!")