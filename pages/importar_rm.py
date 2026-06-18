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
        # 1. Puxa todas as linhas prontas para a integração externa (Status 2)
        resposta_rm = supabase.table("api_rm").select("*").eq("status_rm", 2).execute()
        dados_fila = resposta_rm.data
        
        # 2. Puxa os dados da tabela mestra para resgatar o t_id e t_item solicitados
        resposta_materiais = supabase.table("api_materiais").select("m_coditem, t_id, t_item").execute()
        dados_materiais = resposta_materiais.data
        
    except Exception as e:
        st.error(f"Erro ao consultar a fila no Supabase: {e}")
        dados_fila, dados_materiais = [], []

# ==========================================
# PROCESSAMENTO DOS DADOS COM PANDAS
# ==========================================
if dados_fila:
    df_rm = pd.DataFrame(dados_fila)
    df_mat = pd.DataFrame(dados_materiais)
    
    # Padroniza as colunas de cruzamento como Inteiros limpos
    df_rm["cod_mega"] = pd.to_numeric(df_rm["cod_mega"], errors="coerce").astype("Int64")
    if not df_mat.empty:
        df_mat["m_coditem"] = pd.to_numeric(df_mat["m_coditem"], errors="coerce").astype("Int64")
        
    # Realiza o PROCV em memória trazendo t_id e t_item da tabela mestra baseado no cod_mega
    if not df_mat.empty:
        df_consolidado = pd.merge(df_rm, df_mat, left_on="cod_mega", right_on="m_coditem", how="left")
    else:
        df_consolidado = df_rm.copy()
        df_consolidado["t_id"] = None
        df_consolidado["t_item"] = None

    # TRATAMENTO DE DATAS BRASIL (DD/MM/YYYY)
    # Converte o formato do banco ISO e remove as strings extras de fuso horário
    if "data_necessidade" in df_consolidado.columns:
        df_consolidado["data_necessidade_br"] = pd.to_datetime(df_consolidado["data_necessidade"], errors="coerce").dt.strftime("%d/%m/%Y")
    else:
        df_consolidado["data_necessidade_br"] = "---"

    # Identifica quais RMs únicas estão prontas para criar os blocos visuais na tela
    rms_na_fila = sorted(df_consolidado["n_rm"].dropna().unique())
    
    st.info(f"📦 Encontrada(s) **{len(rms_na_fila)}** RM(s) aguardando envio para a API externa.")
    
    # ==========================================
    # RENDERIZAÇÃO DAS SEÇÕES POR RM VIA LOOP
    # ==========================================
    for num_rm in rms_na_fila:
        # Filtra o DataFrame consolidado trazendo apenas as linhas pertencentes a esta RM específica
        df_rm_atual = df_consolidado[df_consolidado["n_rm"] == num_rm]
        
        with st.expander(f"📋 RM Nº {num_rm} — Fila de Envio ({len(df_rm_atual)} itens)", expanded=True):
            
            # Estrutura a tabela de colunas final contendo as novas solicitações e as ordens alteradas
            linhas_tabela = []
            for _, linha in df_rm_atual.iterrows():
                
                # Tratamento do ID Externo (t_id) para remover decimais residuais do Pandas (.0)
                id_externo_limpo = int(linha["t_id"]) if pd.notna(linha.get("t_id")) else "---"
                
                linhas_tabela.append({
                    # "ID": linha.get("id"),                             # ❌ Ocultado conforme solicitado
                    # "Cód. Solicitação": linha.get("cod_solicitacao_mega"), # ❌ Ocultado conforme solicitado
                    "Seq": linha.get("seq_item"),
                    "ID Externo": id_externo_limpo,                      # 🏢 t_id vindo da api_materiais
                    "Código Mega": linha.get("cod_mega"),
                    "Descrição Externa": linha.get("t_item") if pd.notna(linha.get("t_item")) else "---",  # 📝 t_item vindo da api_materiais
                    "Descrição do Item": linha.get("desc_item"),
                    "Qtd Solicitada": linha.get("qtd_solicitada"),
                    "Data Necessidade": linha.get("data_necessidade_br") # 🇧🇷 Data formatada em português brasileiro
                })
                
            # Gera o DataFrame visual ordenado sequencialmente pelos itens da RM
            df_exibicao = pd.DataFrame(linhas_tabela).sort_values(by="Seq")
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
            
            # ⚡ BOTÃO INDIVIDUALIZADO POR BLOCO DE RM
            if st.button(f"⚡ Enviar e Integrar RM {num_rm} na API Externa", key=f"btn_integrar_{num_rm}", use_container_width=True, type="primary"):
                
                st.subheader(f"🛠️ Iniciando Processamento e chamadas HTTP da RM {num_rm}...")
                
                # -------------------------------------------------------------
                # ESPAÇO RESERVADO PARA A SUA GRANDE LÓGICA DE CHAMADAS HTTP (POST / SET)
                # -------------------------------------------------------------
                # Exemplo de como você vai ler cada linha contendo o ID Externo (t_id) e Código do Mega:
                # for _, linha_item in df_rm_atual.iterrows():
                #     id_externo_chamada = linha_item.get("t_id")
                #     ... aqui faremos a montagem do payload e o requests.post para a API destino ...
                
                st.warning("Área estruturada aguardando a inclusão das regras de envio das chamadas HTTP externas.")
                # -------------------------------------------------------------

else:
    st.info("✨ Tudo em dia! Nenhuma requisição com Status 2 localizada na fila de integração.")
