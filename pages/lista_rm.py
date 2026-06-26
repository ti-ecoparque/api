import streamlit as st
import pandas as pd
import os
from supabase import create_client

# 1. CONFIGURAÇÃO E TRAVA DE SEGURANÇA
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("⚠️ Acesso negado. Por favor, faça login na tela inicial antes de continuar.")
    st.stop()

st.title("📋 Lista e Validação de RMs")
st.write(f"Conectado como: **{st.session_state.get('usuario_email')}**")

# 2. CONEXÃO COM O SUPABASE
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Erro: Credenciais do Supabase não configuradas nos Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# LÓGICA DE FILTROS DE DATAS
# ==========================================
if "filtro_datas_input" not in st.session_state:
    st.session_state.filtro_datas_input = []

def limpar_filtros():
    st.session_state.filtro_datas_input = []

st.divider()
st.subheader("🔍 Filtros de Busca")

with st.form("form_filtros_busca"):
    filtro_datas = st.date_input(
        "Período da Data de Necessidade (Opcional)", 
        value=st.session_state.filtro_datas_input,
        key="datas_temporarias",
        format="DD/MM/YYYY"
    )
    buscar = st.form_submit_button("🔍 Filtrar por Data", use_container_width=True)

st.button("🧹 Limpar Filtros", on_click=limpar_filtros, use_container_width=True)

if buscar:
    st.session_state.filtro_datas_input = filtro_datas

# ==========================================
# REQUISIÇÃO DOS DADOS (TRAZ TUDO STATUS 1)
# ==========================================
with st.spinner("Carregando RMs pendentes..."):
    try:
        query_rm = supabase.table("api_rm").select("*").eq("status_rm", 1)
        
        # Verifica se o usuário selecionou o período completo (Início e Fim)
        if isinstance(st.session_state.filtro_datas_input, (list, tuple)) and len(st.session_state.filtro_datas_input) == 2:
            data_inicio = st.session_state.filtro_datas_input[0].strftime("%Y-%m-%d")
            data_fim = st.session_state.filtro_datas_input[1].strftime("%Y-%m-%d")
            
            query_rm = query_rm.gte("data_necessidade", data_inicio).lte("data_necessidade", data_fim)
        elif isinstance(st.session_state.filtro_datas_input, (list, tuple)) and len(st.session_state.filtro_datas_input) == 1:
            st.info("💡 Selecione a data final no calendário para ativar o filtro de período.")
            
        res_rm = query_rm.execute()
        dados_rm = res_rm.data
        
        # Traz os campos t_item e m_descricao_do_item da lista mestra para o LOG
        res_materiais = supabase.table("api_materiais").select("m_coditem, t_item, m_descricao_do_item").execute()
        dados_materiais = res_materiais.data
        
    except Exception as e:
        st.error(f"Erro ao consultar o banco de dados: {e}")
        dados_rm, dados_materiais = [], []

# ==========================================
# PROCESSAMENTO DO MERGE COM PANDAS
# ==========================================
if dados_rm:
    df_rm = pd.DataFrame(dados_rm)
    df_mat = pd.DataFrame(dados_materiais)
    
    # Força a padronização de tipos primitivos inteiros
    df_rm["cod_mega"] = pd.to_numeric(df_rm["cod_mega"], errors="coerce").astype("Int64")
    if not df_mat.empty:
        df_mat["m_coditem"] = pd.to_numeric(df_mat["m_coditem"], errors="coerce").astype("Int64")
    
    # Realiza o Merge comparando cod_mega com m_coditem
    if not df_mat.empty:
        df_consolidado = pd.merge(df_rm, df_mat, left_on="cod_mega", right_on="m_coditem", how="left")
    else:
        df_consolidado = df_rm.copy()
        df_consolidado["m_descricao_do_item"] = None
        df_consolidado["t_item"] = None

    # Agrupa as RMs dinamicamente por número único presente
    rms_unicas = sorted(df_consolidado["n_rm"].dropna().unique())
    st.write(f"📊 Foram localizadas **{len(rms_unicas)}** RM(s) com itens pendentes.")
    
    # ==========================================
    # RENDERIZAÇÃO DAS SEÇÕES POR RM VIA LOOP
    # ==========================================
    for num_rm in rms_unicas:
        df_rm_atual = df_consolidado[df_consolidado["n_rm"] == num_rm]
        
        with st.expander(f"📦 REQUISIÇÃO DE MATERIAL - RM Nº {num_rm} ({len(df_rm_atual)} itens)", expanded=True):
            linhas_tabela = []
            ids_para_aprovar = []
            lista_logs_para_salvar = []
            contagem_bloqueados = 0
            
            for _, linha in df_rm_atual.iterrows():
                achou = "SIM" if pd.notna(linha.get("m_descricao_do_item")) else "NÃO"
                ids_para_aprovar.append(int(linha["id"]))
                
                if achou == "NÃO":
                    contagem_bloqueados += 1
                else:
                    lista_logs_para_salvar.append({
                        "id_api_rm": int(linha["id"]),
                        "n_rm": int(linha["n_rm"]),
                        "cod_solicitacao_mega": int(linha["cod_solicitacao_mega"]) if pd.notna(linha["cod_solicitacao_mega"]) else None,
                        "cod_mega": int(linha["cod_mega"]) if pd.notna(linha["cod_mega"]) else None,
                        "t_item": str(linha.get("t_item", "")).strip() if pd.notna(linha.get("t_item")) else None,
                        "m_descricao_do_item": str(linha.get("m_descricao_do_item", "")).strip() if pd.notna(linha.get("m_descricao_do_item")) else None,
                        "usuario_logado": str(st.session_state.usuario_email)
                    })
                    
                linhas_tabela.append({
                    "Seq": linha.get("seq_item"),
                    "Cód. Solicitação": linha.get("cod_solicitacao_mega"),
                    "Codigo do Mega": linha.get("cod_mega"),
                    "Descrição RM": linha.get("desc_item"),
                    "Qtd": linha.get("qtd_solicitada"),
                    "Data Necessidade": linha.get("data_necessidade"),
                    "Encontrado no Mestra?": achou,
                    "Descrição Mestra (De/Para)": linha.get("m_descricao_do_item") if achou == "SIM" else "---"
                })
                
            df_exibicao_rm = pd.DataFrame(linhas_tabela).sort_values(by="Seq")
            st.dataframe(df_exibicao_rm, use_container_width=True, hide_index=True)
            
            # ==========================================
            # AÇÃO DE APROVAÇÃO TRANSACIONAL
            # ==========================================
            if contagem_bloqueados == 0:
                st.success(f"✔️ Todos os itens da RM {num_rm} foram validados com sucesso no De/Para.")
                
                if st.button(f"🚀 Aprovar RM {num_rm}", key=f"btn_aprovar_{num_rm}", use_container_width=True, type="primary"):
                    with st.spinner(f"Gravando LOG e salvando aprovação da RM {num_rm}..."):
                        
                        if not lista_logs_para_salvar:
                            st.error("Erro interno: A lista de LOGS está vazia!")
                            st.stop()
                        
                        try:
                            # 🚨 PASSO 1: Salva o instantâneo na tabela de LOGS
                            resposta_log = supabase.table("api_log_rm").insert(lista_logs_para_salvar).execute()
                            
                            if not resposta_log.data or len(resposta_log.data) == 0:
                                st.error("❌ **Falha Crítica de Persistência:** O LOG de segurança não pôde ser salvo!")
                                st.stop()
                            
                            # 🚨 PASSO 2: Altera o status_rm para 2 após garantir a gravação do LOG (Sintaxe Corrigida)
                            resposta_update = (
                                supabase.table("api_rm")
                                .update({"status_rm": 2})
                                .in_("id", ids_para_aprovar)
                                .execute()
                            )
                            
                            if resposta_update.data:
                                st.balloons()
                                st.success(f"🎉 Perfeito! LOG gravado na tabela api_log_rm e RM {num_rm} aprovada para Status 2.")
                                st.rerun()
                        except Exception as e_banco:
                            st.error(f"Erro transacional ao atualizar tabelas: {e_banco}")
else:
    st.info("Nenhuma requisição pendente (Status 1) foi localizada no banco.")
