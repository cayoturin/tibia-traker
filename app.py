import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="MS Analytics Pro", layout="wide", page_icon="🧙‍♂️")

# URL DA PLANILHA (Mantenha a sua URL aqui)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1QPOI0BRolnICnLu7hDKz5WrtiqNLlq7-CkuPdiaMkv4/edit?usp=sharing"

# --- FUNÇÕES UTILITÁRIAS ---
def xp_for_level(level):
    return int((50/3) * (level**3 - 6*level**2 + 17*level - 12))

def format_number(num):
    if num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}k"
    return str(num)

# --- CONEXÃO E DADOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(spreadsheet=SHEET_URL, ttl=0)
        required_columns = ["Data", "Level", "Local", "Tempo (min)", "XP Total", "XP/h Real", "Lucro", "Supplies"]
        
        # Blindagem contra planilha vazia ou colunas erradas
        if data.empty or not set(required_columns).issubset(data.columns):
            return pd.DataFrame(columns=required_columns)
        
        # Converter coluna de Data para Datetime para permitir gráficos de tempo
        data['Data'] = pd.to_datetime(data['Data'], errors='coerce')
        return data
    except Exception:
        return pd.DataFrame(columns=["Data", "Level", "Local", "Tempo (min)", "XP Total", "XP/h Real", "Lucro", "Supplies"])

def save_hunt(log_text, location, level):
    try:
        import re
        def clean_num(label):
            match = re.search(rf"{label}: ([\d,.\-]+)", log_text)
            return int(match.group(1).replace(',', '').replace('.', '')) if match else 0

        xp = clean_num('XP Gain')
        loot = clean_num('Loot')
        supplies = clean_num('Supplies')
        balance = clean_num('Balance')
        
        time_match = re.search(r'Session: (\d+):(\d+)h', log_text)
        minutes = (int(time_match.group(1)) * 60) + int(time_match.group(2)) if time_match else 0
        xp_h_real = (xp / minutes) * 60 if minutes > 0 else 0

        new_row = [datetime.now().strftime("%Y-%m-%d %H,%M"), int(level), location, minutes, xp, int(xp_h_real), balance, supplies]
        return new_row
    except Exception as e:
        st.error(f"Erro ao ler log: {e}")
        return None

# --- CARREGAMENTO INICIAL ---
df = load_data()
current_lvl = int(df["Level"].max()) if not df.empty and "Level" in df.columns else 157

# --- SIDEBAR (INPUT COM SENHA) ---
with st.sidebar:
    st.header("🔐 Área Restrita")
    
    # Campo de senha
    password = st.text_input("Digite a senha para editar", type="password")
    
    # Definimos a sua senha secreta aqui (TROQUE 'tibia123' pela sua)
    SENHA_CORRETA = "tibia123"

    if password == SENHA_CORRETA:
        st.success("Acesso liberado!")
        st.markdown("---")
        st.header("📝 Nova Sessão")
        in_lvl = st.number_input("Level", value=current_lvl)
        in_loc = st.text_input("Local", "Lava Lurkers")
        in_log = st.text_area("Log do Analyser")
        
        if st.button("💾 Salvar Hunt", type="primary"):
            row = save_hunt(in_log, in_loc, in_lvl)
            if row:
                df_new = pd.DataFrame([row], columns=["Data", "Level", "Local", "Tempo (min)", "XP Total", "XP/h Real", "Lucro", "Supplies"])
                updated_df = pd.concat([df, df_new], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.success("Salvo com sucesso!")
                st.rerun()
    elif password == "":
        st.info("Insira a senha para habilitar o envio de dados.")
    else:
        st.error("Senha incorreta. Apenas visualização permitida.")

# --- TÍTULO E ABAS ---
st.title(f"🧙‍♂️ MS Level {current_lvl} - Analytics")

# Criando "Páginas" usando Abas
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Visão Geral", "📈 Evolução (Time Series)", "⚔️ Comparativo de Hunts", "🏆 Hall of Fame", "Calculadora de Imbuemenst", "Bestiary Progress"])

# --- ABA 1: VISÃO GERAL (RESUMO) ---
with tab1:
    if not df.empty:
        st.subheader("🚀 Evolução do Personagem")
        # Gráfico de área para dar peso visual ao crescimento
        fig_evolucao = px.area(df, x="Data", y="Level", 
                              title="Crescimento ao Longo do Tempo",
                              labels={'Level': 'Nível', 'Data': 'Data da Hunt'},
                              color_discrete_sequence=['#00CC96']) # Verde MS
        
        # Ajuste para o gráfico ficar limpo
        fig_evolucao.update_layout(xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig_evolucao, use_container_width=True)

    if not df.empty:
        # KPI Cards
        xp_total = df["XP Total"].sum()
        lucro_total = df["Lucro"].sum()
        horas_jogs = df["Tempo (min)"].sum() / 60
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total XP Farmada", format_number(xp_total), help="Soma de todas as hunts")
        c2.metric("Lucro Líquido", format_number(lucro_total), delta_color="normal")
        c3.metric("Horas Jogadas", f"{horas_jogs:.1f}h")
        c4.metric("Hunts Registradas", len(df))

        # Barra de Progresso Lvl 400
        xp_next = xp_for_level(400) - xp_for_level(current_lvl)
        st.write(f"**Road to Level 400** (Faltam {format_number(xp_next)} XP)")
        st.progress(min(xp_for_level(current_lvl)/xp_for_level(400), 1.0))
        
        st.subheader("Últimas 5 Hunts")
        st.dataframe(df.tail(5).sort_values("Data", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.warning("Sem dados. Adicione sua primeira hunt na barra lateral.")

# --- ABA 2: EVOLUÇÃO TEMPORAL (TIPO BOLSA DE VALORES) ---
with tab2:
    if not df.empty:
        st.subheader("📅 Evolução Diária de XP")
        
        # Agrupar dados por dia
        daily_xp = df.groupby(df['Data'].dt.date)['XP Total'].sum().reset_index()
        daily_xp.columns = ['Data', 'XP do Dia']
        
        # Gráfico Financeiro com Range Slider
        fig_timeline = px.line(daily_xp, x='Data', y='XP do Dia', markers=True, title="XP Ganha por Dia")
        
        # Adicionar o "Seletor de Range" (Igual grafico de ações)
        fig_timeline.update_xaxes(
            rangeslider_visible=True,
            rangeselector=dict(
                buttons=list([
                    dict(count=7, label="1 Sem", step="day", stepmode="backward"),
                    dict(count=1, label="1 Mês", step="month", stepmode="backward"),
                    dict(step="all", label="Tudo")
                ])
            )
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        st.caption("Use os botões '1 Sem' ou arraste a barra inferior para dar zoom em períodos específicos.")

# --- ABA 3: COMPARATIVO DE HUNTS (RAIO-X) ---
with tab3:
    if not df.empty:
        st.subheader("🔍 Qual hunt vale mais a pena?")
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            # Gráfico de Dispersão: XP/h vs Lucro (Magic Quadrant)
            # Isso mostra qual hunt dá muita XP e muito Lucro ao mesmo tempo
            fig_scatter = px.scatter(
                df, 
                x="Lucro", 
                y="XP/h Real", 
                color="Local", 
                size="XP Total", 
                hover_data=["Data", "Tempo (min)"],
                title="Matriz de Eficiência: XP vs Lucro"
            )
            # Adiciona linhas de zero para ver o que é prejuízo
            fig_scatter.add_vline(x=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_scatter, use_container_width=True)
            st.info("Bolhas na **Direita e Alto** são as melhores hunts (Lucro + XP). Bolhas na **Esquerda** são Waste.")

        with col_graf2:
            # Comparativo Médio por Local
            media_por_local = df.groupby("Local")[["XP/h Real", "Lucro"]].mean().reset_index()
            fig_bar = px.bar(
                media_por_local, 
                x="Local", 
                y="XP/h Real", 
                color="Lucro",
                color_continuous_scale="RdYlGn",
                title="Média de XP/h por Respawn"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

# --- ABA 4: HALL OF FAME (RECORDES) ---
with tab4:
    if not df.empty:
        st.subheader("🏆 Seus Recordes Pessoais")
        
        # Encontrar recordes
        best_xp_idx = df['XP/h Real'].idxmax()
        best_profit_idx = df['Lucro'].idxmax()
        max_waste_idx = df['Lucro'].idxmin()
        
        best_xp_hunt = df.loc[best_xp_idx]
        best_profit_hunt = df.loc[best_profit_idx]
        worst_waste_hunt = df.loc[max_waste_idx]

        c_rec1, c_rec2, c_rec3 = st.columns(3)
        
        with c_rec1:
            st.success("🚀 Maior XP/h")
            st.metric(label=best_xp_hunt['Local'], value=format_number(best_xp_hunt['XP/h Real']))
            st.caption(f"Em {best_xp_hunt['Data'].strftime('%d/%m')}")

        with c_rec2:
            st.success("💰 Maior Lucro")
            st.metric(label=best_profit_hunt['Local'], value=format_number(best_profit_hunt['Lucro']))
            st.caption("Fez a boa!")

        with c_rec3:
            st.error("💸 Maior Prejuízo (Investimento)")
            st.metric(label=worst_waste_hunt['Local'], value=format_number(worst_waste_hunt['Lucro']))
            st.caption("Full rush mode")
            
        st.markdown("---")
        st.markdown("### Histórico Completo")
        # Tabela completa pesquisável
        st.dataframe(df, use_container_width=True)
        
# --- ABA 5: CALCULADORA DE IMBUEMENTS ---
with tab5:
    st.subheader("💰 Calculadora de Custo/Benefício")
    col_i1, col_i2 = st.columns(2)
    
    with col_i1:
        st.write("**Preços do Market**")
        token_price = st.number_input("Preço da Gold Token", value=45000)
        st.markdown("---")
        st.write("Exemplo: Powerful Strike (Crit)")
        item1 = st.number_input("Protective Charm (20x)", value=2500)
        item2 = st.number_input("Sabretooth (25x)", value=6000)
        item3 = st.number_input("Vexclaw Talon (5x)", value=2000)
        taxa = 300000 # Taxa de criação do Powerful
    
    with col_i2:
        custo_itens = (item1 * 20) + (item2 * 25) + (item3 * 5) + taxa
        custo_tokens = (token_price * 6) + taxa # 6 tokens para Powerful
        
        st.write("**Comparativo (20 horas)**")
        st.metric("Custo com Itens", f"{custo_itens:,} gp")
        st.metric("Custo com Tokens", f"{custo_tokens:,} gp")
        
        melhor_opcao = "ITENS" if custo_itens < custo_tokens else "GOLD TOKENS"
        st.success(f"🏆 Melhor opção: **{melhor_opcao}**")
        
        custo_hora = min(custo_itens, custo_tokens) / 20
        st.metric("🔥 Impacto na Hunt", f"{custo_hora:,.0f} gp/h", help="Subtraia isso do seu lucro por hora")

# --- ABA 6: RASTREADOR DE BESTIARY ---

import streamlit as st
import json

# Função para carregar o arquivo
def load_bestiary():
    with open('bestiary.json', 'r', encoding='utf-8') as f:
        return json.load(f)

bestiario = load_bestiary()

st.header("📜 Bestiários Completos")

# Escolha da Categoria
cat = st.selectbox("Filtrar por Categoria", list(bestiario.keys()))

# Multiselect com os monstros da categoria
monstros_da_cat = bestiario[cat]
concluidos = st.multiselect(f"Monstros de {cat} concluídos:", monstros_da_cat)

# Barra de progresso da categoria
if monstros_da_cat:
    prog = len(concluidos) / len(monstros_da_cat)
    st.progress(prog)
    st.write(f"Você completou {len(concluidos)} de {len(monstros_da_cat)} nesta categoria.")










