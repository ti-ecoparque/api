import streamlit as st
import pandas as pd
import os
from datetime import datetime
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

# ==========================================
# RECURSOS VISUAIS E FILTROS DA INTERFACE
# ==========================================
st.divider()
st.subheader("🔍 Filtros de Busca")

col1, col2 = st.columns(2)

with col1:
    # Filtro opcional por número de RM
    filtro_rm = st.text_input("Número da RM (Opcional)", placeholder="Ex: 2484")

with col2:
    # Filtro opcional por intervalo de data (data_necessidade)
    filtro_datas = st.date_input(
        "Período da Data de Necessidade (Opcional)", 
        value=[], 
        format="DD/MM/YYYY"
    )

# ==========================================
# CONSTRUÇÃO DA CONSULTA COM INNER JOIN
# ==========================================
# Iniciamos a query na tabela principal buscando apenas status_rm = 1
query = supabase.table("api_rm").select(
    "id, n_rm, seq_item, cod_solicitacao_mega, desc_item, qtd_solicitada, data_necessidade, status_rm, "
    "api_materiais(m_coditem, m_descricao_do_item)" # Realiza o Join com a tabela mestra automaticamente
).eq("status_rm", 1)

# Aplica filtros dinâmicos se o usuário preencher
if filtro_rm:
    try:
        query = query.eq("n_rm", int(filtro_rm))
    except ValueError:
        st.error("Por favor, digite um número válido para a RM.")

if len(filtro_datas) == 2:
    data_inicio = filtro_datas[0].strftime("%Y-%m-%d")
    data_fim = filtro_datas[1].strftime("%Y-%m-%d")
    query = query.gte("data_necessidade", data_inicio).lte("data_necessidade", data_fim)

# Executa a busca no Supabase
with st.spinner("Buscando dados no banco..."):
    try:
        resposta = query.execute()
        dados_brutos = resposta.data
    except Exception as e:
        st.error(f"Erro ao consultar o banco de dados: {e}")
        dados_brutos = []

# ==========================================
# PROCESSAMENTO E EXIBIÇÃO DOS DADOS
# ==========================================
if dados_brutos:
    # Transforma o JSON de retorno em uma tabela Pandas para manipulação sutil
    linhas_tabela = []
    
    for item in dados_brutos:
        # Extrai os dados internos da tabela vinculada pelo Join (se existirem)
        dados_mestra = item.get("api_materiais")
        
        encontrado_na_mestra = "NÃO"
        desc_mestra = "---"
        
        if dados_mestra:
            encontrado_na_mestra = "SIM"
            desc_mestra = dados_mestra.get("m_descricao_do_item", "---")
        
        linhas_tabela.append({
            "ID Banco": item.get("id"),
            "Nº RM": item.get("n_rm"),
            "Seq": item.get("seq_item"),
            "Cód. Solicitação": item.get("cod_solicitacao_mega"),
            "Descrição RM": item.get("desc_item"),
            "Qtd": item.get("qtd_solicitada"),
            "Data Necessidade": item.get("data_necessidade"),
            "Encontrado no Mestra?": encontrado_na_mestra,
            "Descrição Mestra (De/Para)": desc_mestra
        })
    
    df_exibicao = pd.DataFrame(linhas_tabela)
    
    # Separa os IDs das linhas que cumprem o requisito (encontrados na tabela mestra)
    ids_validos_para_atualizar = [
        linha["ID Banco"] for linha in linhas_tabela if linha["Encontrado no Mestra?"] == "SIM"
    ]
    
    st.write(f"📊 Foram encontrados **{len(df_exibicao)}** itens pendentes (Status 1).")
    
    # Exibe a tabela formatada na tela
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Mapeia as estatísticas para o operador
    total_validos = len(ids_validos_para_atualizar)
    total_invalidos = len(df_exibicao) - total_validos
    
    col_stat1, col_stat2 = st.columns(2)
    col_stat1.metric("Itens Prontos para Alterar (Status 2)", total_validos)
    col_stat2.metric("Itens Bloqueados (Não achou no De/Para)", total_invalidos)
    
    # ==========================================
    # AÇÃO DE ATUALIZAÇÃO EM LOTE
    # ==========================================
    if total_validos > 0:
        if st.button(f"🔄 Mudar Status para '2' de ({total_validos}) itens validados", type="primary", use_container_width=True):
            with st.spinner("Atualizando registros elegíveis..."):
                try:
                    # Executa o UPDATE apenas para a lista de IDs válidos de uma vez só (.in_)
                    resposta_update = supabase.table("api_rm")\
                        .update({"status_rm": 2})\
                        .in_("id", ids_validos_para_atualizar)\
                        .execute()
                    
                    if resposta_update.data:
                        st.balloons()
                        st.success(f"🎉 Sucesso! {len(resposta_update.data)} itens foram atualizados para o Status 2.")
                        st.rerun() # Atualiza a tela para sumir com os itens modificados
                except Exception as erro_up:
                    st.error(f"Erro ao tentar processar a atualização no banco: {erro_up}")
    else:
        st.warning("⚠️ Nenhum dos itens listados acima está cadastrado na tabela 'api_materiais'. A alteração de status está bloqueada.")

else:
    st.info("Nenhuma requisição pendente (Status 1) foi localizada com os filtros aplicados.")
