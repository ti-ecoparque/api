import streamlit as st
import pandas as pd
import os
import requests
from supabase import create_client

# 1. CONFIGURAÇÃO E TRAVA DE SEGURANÇA (Obrigatórios no topo)
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("⚠️ Acesso negado. Por favor, faça login na tela inicial antes de continuar.")
    st.stop()

st.title("🚀 Fila de Integração - Envio de RMs")
st.write(f"Operador: **{st.session_state.get('usuario_email')}**")

# 2. CONEXÃO COM O SUPABASE
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Erro: Credenciais do Supabase não configuradas nos Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.divider()

# ==========================================
# REQUISIÇÃO DOS DADOS (FILTRA STATUS_RM == 2)
# ==========================================
with st.spinner("Buscando requisições aprovadas na fila (Status 2)..."):
    try:
        # Puxa todas as linhas prontas para a integração externa
        resposta = supabase.table("api_rm").select("*").eq("status_rm", 2).execute()
        dados_fila = resposta.data
    except Exception as e:
        st.error(f"Erro ao consultar a fila no Supabase: {e}")
        dados_fila = []

# ==========================================
# PROCESSAMENTO VISUAL POR RM
# ==========================================
if dados_fila:
    df_fila = pd.DataFrame(dados_fila)
    
    # Identifica quais RMs únicas estão na fila de envio para criar os blocos na tela
    rms_na_fila = sorted(df_fila["n_rm"].dropna().unique())
    
    st.info(f"📦 Encontrada(s) **{len(rms_na_fila)}** RM(s) aguardando envio para a API externa.")
    
    # Laço que gera uma seção visual e um botão para cada RM de forma isolada
    for num_rm in rms_na_fila:
        # Filtra o DataFrame trazendo apenas os itens desta RM específica
        df_rm_atual = df_fila[df_fila["n_rm"] == num_rm]
        
        with st.expander(f"📋 RM Nº {num_rm} — Fila de Envio ({len(df_rm_atual)} itens)", expanded=True):
            
            # Monta a tabela limpa para exibição na tela
            linhas_tabela = []
            for _, linha in df_rm_atual.iterrows():
                linhas_tabela.append({
                    "ID": linha.get("id"),
                    "Seq": linha.get("seq_item"),
                    "Cód. Solicitação": linha.get("cod_solicitacao_mega"),
                    "Código Mega": linha.get("cod_mega"),
                    "Descrição do Item": linha.get("desc_item"),
                    "Qtd Solicitada": linha.get("qtd_solicitada"),
                    "Data Necessidade": linha.get("data_necessidade")
                })
                
            df_exibicao = pd.DataFrame(linhas_tabela).sort_values(by="Seq")
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
            
            # 🔹 SEU BOTÃO INDIVIDUALIZADO POR RM:
            # A chave 'key' garante que cada botão na tela seja único baseado no número da RM
            if st.button(f"⚡ Enviar e Integrar RM {num_rm} na API Externa", key=f"btn_integrar_{num_rm}", use_container_width=True, type="primary"):
                
                # -------------------------------------------------------------
                # ESPAÇO RESERVADO PARA A SUA GRANDE LÓGICA DE INTEGRAÇÃO
                # -------------------------------------------------------------
                st.subheader(f"🛠️ Executando Processamento da RM {num_rm}...")
                
                # Exemplo de como você vai percorrer as linhas dessa RM no próximo passo:
                # for _, linha_item in df_rm_atual.iterrows():
                #     ... aqui faremos a sua Procv com a tabela mestra e chamadas HTTP POST/SET ...
                
                st.warning("Área reservada para inclusão da lógica de chamada HTTP externa.")
                # -------------------------------------------------------------

else:
    st.info("✨ Tudo em dia! Nenhuma requisição com Status 2 localizada na fila de integração.")
