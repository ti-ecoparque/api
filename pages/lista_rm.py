import streamlit as st
import pandas as pd
import os
from supabase import create_client

# 1. TRAVA DE SEGURANÇA E CONFIGURAÇÃO
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
# LÓGICA DE LIMPEZA DE FILTROS
# ==========================================
def limpar_filtros():
    st.session_state.filtro_rm_input = ""
    st.session_state.filtro_datas_input = []

# Inicializa os estados das caixas se não existirem
if "filtro_rm_input" not in st.session_state:
    st.session_state.filtro_rm_input = ""
if "filtro_datas_input" not in st.session_state:
    st.session_state.filtro_datas_input = []

# ==========================================
# INTERFACE GRÁFICA DE FILTROS
# ==========================================
st.divider()
st.subheader("🔍 Filtros de Busca")

with st.form("form_filtros_busca"):
    col1, col2 = st.columns(2)
    with col1:
        # Forçamos o campo a ler e guardar o valor no session_state para permitir a limpeza
        filtro_rm = st.text_input(
            "Número da RM (Obrigatório para validação)", 
            value=st.session_state.filtro_rm_input,
            key="rm_temporaria",
            placeholder="Ex: 1464"
        )
    with col2:
        filtro_datas = st.date_input(
            "Período da Data de Necessidade (Opcional)", 
            value=st.session_state.filtro_datas_input,
            key="datas_temporarias",
            format="DD/MM/YYYY"
        )
        
    col_btn_busca, col_btn_limpar = st.columns([1, 1])
    with col_btn_busca:
        buscar = st.form_submit_button("🔍 Executar Busca", use_container_width=True)

# Botão de limpar filtros colocado de forma nativa fora do formulário para disparar o on_click
st.button("🧹 Limpar Filtros", on_click=limpar_filtros, use_container_width=True)

# ==========================================
# PROCESSAMENTO E REQUISIÇÕES
# ==========================================
if buscar:
    # 🚨 REGRA DE NEGÓCIO 1: Bloqueia a busca se não digitar o número da RM
    if not filtro_rm:
        st.warning("⚠️ Para validar o De/Para e avançar o status, informe o Número da RM obrigatoriamente.")
        st.stop()
        
    # Salva os dados pesquisados atuais na sessão
    st.session_state.filtro_rm_input = filtro_rm
    st.session_state.filtro_datas_input = filtro_datas

    with st.spinner("Consultando dados e validando com a lista mestra..."):
        try:
            # Busca estritamente os itens da RM informada que estão pendentes (Status 1)
            query_rm = supabase.table("api_rm").select("*").eq("status_rm", 1).eq("n_rm", int(filtro_rm))
            
            if len(filtro_datas) == 2:
                query_rm = query_rm.gte("data_necessidade", filtro_datas[0].strftime("%Y-%m-%d"))\
                                   .lte("data_necessidade", filtro_datas[1].strftime("%Y-%m-%d"))
                
            res_rm = query_rm.execute()
            dados_rm = res_rm.data
            
            # Busca a tabela mestra inteira para bater os códigos em memória
            res_materiais = supabase.table("api_materiais").select("m_coditem, m_descricao_do_item").execute()
            dados_materiais = res_materiais.data
            
        except Exception as e:
            st.error(f"Erro ao consultar o banco de dados: {e}")
            dados_rm, dados_materiais = [], []

    # CRUZAMENTO DE DADOS (MERGE/PROCV)
    if dados_rm:
        df_rm = pd.DataFrame(dados_rm)
        df_mat = pd.DataFrame(dados_materiais)
        
        # Alinha os tipos de dados para inteiros
        df_rm['cod_mega'] = pd.to_numeric(df_rm['cod_mega'], errors='coerce').astype('Int64')
        if not df_mat.empty:
            df_mat['m_coditem'] = pd.to_numeric(df_mat['m_coditem'], errors='coerce').astype('Int64')
        
        # Realiza o Merge comparando cod_mega com m_coditem
        if not df_mat.empty:
            df_consolidado = pd.merge(df_rm, df_mat, left_on='cod_mega', right_on='m_coditem', how='left')
        else:
            df_consolidado = df_rm.copy()
            df_consolidado['m_descricao_do_item'] = None

        linhas_tabela = []
        ids_da_rm_atual = []
        contagem_nao_encontrados = 0
        
        for _, linha in df_consolidado.iterrows():
            achou = "SIM" if pd.notna(linha.get("m_descricao_do_item")) else "NÃO"
            
            # Coleta todos os IDs de registros pertencentes a esta RM filtrada
            ids_da_rm_atual.append(int(linha["id"]))
            
            if achou == "NÃO":
                contagem_nao_encontrados += 1
                
            linhas_tabela.append({
                "Nº RM": linha.get("n_rm"),
                "Cód. Solicitação": linha.get("cod_solicitacao_mega"),
                "Seq": linha.get("seq_item"),
                "Codigo do Mega": linha.get("cod_mega"),
                "Descrição RM": linha.get("desc_item"),
                "Qtd": linha.get("qtd_solicitada"),
                "Data Necessidade": linha.get("data_necessidade"),
                "Encontrado no Mestra?": achou,
                "Descrição Mestra (De/Para)": linha.get("m_descricao_do_item") if achou == "SIM" else "---"
            })
            
        df_exibicao = pd.DataFrame(linhas_tabela)
        
        st.write(f"📋 **Itens da RM {filtro_rm} pendentes de aprovação:**")
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        
        st.divider()
        
        total_itens_rm = len(df_exibicao)
        total_prontos = total_itens_rm - contagem_nao_encontrados
        
        col_stat1, col_stat2 = st.columns(2)
        col_stat1.metric("Itens Encontrados (Válidos)", total_prontos)
        col_stat2.metric("Itens Faltantes (Bloqueados)", contagem_nao_encontrados)
        
        # ==========================================
        # 🚨 REGRA DE VALIDAÇÃO CRÍTICA (TUDO OU NADA)
        # ==========================================
        # Só libera a mudança de status para 2 se NÃO houver nenhum item marcado como 'NÃO'
        if contagem_nao_encontrados == 0:
            st.success(f"🎉 Excelente! Todos os **{total_itens_rm}** itens da RM {filtro_rm} foram validados na lista mestra.")
            
            # Atualiza o status de 1 para 2 de todos os itens dessa RM de uma vez só
            if st.button(f"🚀 Aprovar RM {filtro_rm} (Mudar para Status 2)", type="primary", use_container_width=True):
                with st.spinner("Registrando aprovação da RM..."):
                    try:
                        resposta_update = supabase.table("api_rm")\
                            .update({"status_rm": 2})\
                            .in_("id", ids_da_rm_atual)\
                            .execute()
                        
                        if respuesta_update.data:
                            st.balloons()
                            st.success(f"RM {filtro_rm} aprovada por completo e enviada para a fila de integração (Status 2)!")
                            limpar_filtros()
                            st.rerun()
                    except Exception as erro_up:
                        st.error(f"Erro ao processar atualização da RM: {erro_up}")
        else:
            # Bloqueia a operação jogando um alerta explicativo na interface
            st.error(
                f"❌ **Aprovação Bloqueada:** Existem **{contagem_nao_encontrados}** item(ns) nesta RM que não possuem correspondência "
                f"na tabela 'api_materiais'. Cadastre os códigos pendentes na lista mestra antes de tentar liberar a RM."
            )
            st.button(f"🔒 Mudar Status Bloqueado (Ajuste os {contagem_nao_encontrados} itens)", disabled=True, use_container_width=True)
            
    else:
        st.info(f"Nenhum item pendente (Status 1) localizado para a RM **{filtro_rm}**.")
