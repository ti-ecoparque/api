import streamlit as st
import pandas as pd
import os
from supabase import create_client

# 1. TRAVA DE SEGURANÇA E CONFIGURAÇÃO
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("Acesso negado. Por favor, faça login na tela inicial antes de continuar.")
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

# Filtros da Interface
st.divider()
st.subheader("🔍 Filtros de Busca")

col1, col2 = st.columns(2)
with col1:
    filtro_rm = st.text_input("Número da RM (Opcional)", placeholder="Ex: 2484")
with col2:
    filtro_datas = st.date_input("Período da Data de Necessidade (Opcional)", value=[], format="DD/MM/YYYY")

# ==========================================
# BUSCA DOS DADOS SEPARADOS (SEM INNER JOIN)
# ==========================================
with st.spinner("Buscando dados no banco..."):
    try:
        # 1. Busca os itens da api_rm com status 1
        query_rm = supabase.table("api_rm").select("*").eq("status_rm", 1)
        
        if filtro_rm:
            query_rm = query_rm.eq("n_rm", int(filtro_rm))
        if len(filtro_datas) == 2:
            query_rm = query_rm.gte("data_necessidade", filtro_datas[0].strftime("%Y-%m-%d")).lte("data_necessidade", filtro_datas[1].strftime("%Y-%m-%d"))
            
        res_rm = query_rm.execute()
        dados_rm = res_rm.data
        
        # 2. Busca a tabela mestra inteira para cruzar em memória
        res_materiais = supabase.table("api_materiais").select("m_coditem, m_descricao_do_item").execute()
        dados_materiais = res_materials = res_materiais.data
        
    except Exception as e:
        st.error(f"Erro ao consultar o banco de dados: {e}")
        dados_rm, dados_materiais = [], []

# ==========================================
# PROCESSAMENTO DOS DADOS COM PANDAS
# ==========================================
if dados_rm:
    # Transforma os dados em DataFrames do Pandas
    df_rm = pd.DataFrame(dados_rm)
    df_mat = pd.DataFrame(dados_materials)
    
    # Força os códigos de comparação a serem do mesmo tipo (Texto ou Inteiro limpo)
    df_rm['cod_solicitacao_mega'] = pd.to_numeric(df_rm['cod_solicitacao_mega'], errors='coerce').astype('Int64')
    if not df_mat.empty:
        df_mat['m_coditem'] = pd.to_numeric(df_mat['m_coditem'], errors='coerce').astype('Int64')
    
    # Executa o cruzamento de dados (Equivalente ao PROCV / INNER JOIN) em memória
    if not df_mat.empty:
        df_consolidado = pd.merge(
            df_rm, 
            df_mat, 
            left_on='cod_solicitacao_mega', 
            right_on='m_coditem', 
            how='left'
        )
    else:
        df_consolidado = df_rm.copy()
        df_consolidado['m_descricao_do_item'] = None

    # Monta a estrutura final de exibição na tela
    linhas_tabela = []
    ids_validos_para_atualizar = []
    
    for _, linha in df_consolidado.iterrows():
        # Se encontrou a descrição na tabela mestra, valida o item
        achou = "SIM" if pd.notna(linha.get("m_descricao_do_item")) else "NÃO"
        
        if achou == "SIM":
            ids_validos_para_atualizar.append(int(linha["id"]))
            
        linhas_tabela.append({
            "ID Banco": linha.get("id"),
            "Nº RM": linha.get("n_rm"),
            "Seq": linha.get("seq_item"),
            "Cód. Solicitação": linha.get("cod_solicitacao_mega"),
            "Descrição RM": linha.get("desc_item"),
            "Qtd": linha.get("qtd_solicitada"),
            "Data Necessidade": linha.get("data_necessidade"),
            "Encontrado no Mestra?": achou,
            "Descrição Mestra (De/Para)": linha.get("m_descricao_do_item") if achou == "SIM" else "---"
        })
        
    df_exibicao = pd.DataFrame(linhas_tabela)
    st.write(f"📊 Foram encontrados **{len(df_exibicao)}** itens pendentes (Status 1).")
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
    
    st.divider()
    total_validos = len(ids_validos_para_atualizar)
    total_invalidos = len(df_exibicao) - total_validos
    
    col_stat1, col_stat2 = st.columns(2)
    col_stat1.metric("Itens Prontos para Alterar (Status 2)", total_validos)
    col_stat2.metric("Itens Bloqueados (Não achou no De/Para)", total_invalidos)
    
    # Botão de Ação em Lote
    if total_validos > 0:
        if st.button(f"🔄 Mudar Status para '2' de ({total_validos}) itens validados", type="primary", use_container_width=True):
            with st.spinner("Atualizando registros elegíveis..."):
                try:
                    resposta_update = supabase.table("api_rm")\
                        .update({"status_rm": 2})\
                        .in_("id", ids_validos_para_atualizar)\
                        .execute()
                    
                    if resposta_update.data:
                        st.balloons()
                        st.success(f"🎉 Sucesso! {len(resposta_update.data)} itens atualizados para o Status 2.")
                        st.rerun()
                except Exception as erro_up:
                    st.error(f"Erro ao atualizar no banco: {erro_up}")
    else:
        st.warning("⚠️ Nenhum item está cadastrado na tabela 'api_materiais'. Alteração de status bloqueada.")
else:
    st.info("Nenhuma requisição pendente (Status 1) localizada.")
