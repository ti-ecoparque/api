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
# LÓGICA DE LIMPEZA E ESTADO DE FILTROS
# ==========================================
if "filtro_datas_input" not in st.session_state:
    st.session_state.filtro_datas_input = []

def limpar_filtros():
    st.session_state.filtro_datas_input = []

st.divider()
st.subheader("🔍 Filtros de Busca")

# Formulário apenas para o filtro de datas (Opcional)
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
        # Busca TODOS os itens pendentes (Status 1) do banco
        query_rm = supabase.table("api_rm").select("*").eq("status_rm", 1)
        
        # Aplica o filtro de data se houver período selecionado
        if len(st.session_state.filtro_datas_input) == 2:
            query_rm = query_rm.gte("data_necessidade", st.session_state.filtro_datas_input[0].strftime("%Y-%m-%d"))\
                               .lte("data_necessidade", st.session_state.filtro_datas_input[1].strftime("%Y-%m-%d"))
            
        res_rm = query_rm.execute()
        dados_rm = res_rm.data
        
        # Busca a tabela mestra inteira para bater os códigos em memória
        res_materiais = supabase.table("api_materiais").select("m_coditem, m_descricao_do_item").execute()
        dados_materiais = res_materiais.data
        
    except Exception as e:
        st.error(f"Erro ao consultar o banco de dados: {e}")
        dados_rm, dados_materiais = [], []

# ==========================================
# PROCESSAMENTO EM MEMÓRIA COM PANDAS
# ==========================================
if dados_rm:
    df_rm = pd.DataFrame(dados_rm)
    df_mat = pd.DataFrame(dados_materiais)
    
    # Padroniza chaves para números inteiros
    df_rm["cod_mega"] = pd.to_numeric(df_rm["cod_mega"], errors="coerce").astype("Int64")
    if not df_mat.empty:
        df_mat["m_coditem"] = pd.to_numeric(df_mat["m_coditem"], errors="coerce").astype("Int64")
    
    # Realiza o Merge comparando cod_mega com m_coditem
    if not df_mat.empty:
        df_consolidado = pd.merge(df_rm, df_mat, left_on="cod_mega", right_on="m_coditem", how="left")
    else:
        df_consolidado = df_rm.copy()
        df_consolidado["m_descricao_do_item"] = None

    # Descobre todas as RMs únicas que estão na lista para gerar os blocos na tela
    rms_unicas = sorted(df_consolidado["n_rm"].dropna().unique())
    
    st.write(f"📊 Foram localizadas **{len(rms_unicas)}** RM(s) com itens pendentes.")
    
    # ==========================================
    # LAÇO REPETITIVO: GERA UMA SEÇÃO POR RM
    # ==========================================
    for num_rm in rms_unicas:
        # Filtra o DataFrame consolidado trazendo apenas os registros desta RM específica
        df_rm_atual = df_consolidado[df_consolidado["n_rm"] == num_rm]
        
        # Cria uma caixa expansível visual organizada para cada RM separada
        with st.expander(f"📦 REQUISIÇÃO DE MATERIAL - RM Nº {num_rm} ({len(df_rm_atual)} itens)", expanded=True):
            
            linhas_tabela = []
            ids_para_aprovar = []
            contagem_bloqueados = 0
            
            # Varre os itens da RM atual para montar a tabela visual
            for _, linha in df_rm_atual.iterrows():
                achou = "SIM" if pd.notna(linha.get("m_descricao_do_item")) else "NÃO"
                
                # Guarda o ID do banco para o processo de update em lote individual
                ids_para_aprovar.append(int(linha["id"]))
                
                if achou == "NÃO":
                    contagem_bloqueados += 1
                    
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
            
            # Desenha a tabela específica desta RM na tela
            st.dataframe(df_exibicao_rm, use_container_width=True, hide_index=True)
            
            # Lógica de validação "Tudo ou Nada" por bloco de RM
            if contagem_bloqueados == 0:
                st.success(f"✔️ Todos os itens da RM {num_rm} foram validados com sucesso no De/Para.")
                
                # Botão de aprovação individual exclusivo desta RM
                if st.button(f"🚀 Aprovar RM {num_rm}", key=f"btn_aprovar_{num_rm}", use_container_width=True, type="primary"):
                    with st.spinner(f"Atualizando RM {num_rm}..."):
                        try:
                            resposta_update = supabase.table("api_rm")\
                                .update({"status_rm": 2})\
                                .in_("id", ids_para_aprovar)\
                                .execute()
                            
                            if resposta_update.data:
                                st.balloons()
                                st.success(f"🎉 RM {num_rm} atualizada com sucesso para o Status 2!")
                                st.rerun()
                        except Exception as error_up:
                            st.error(f"Erro ao atualizar banco: {error_up}")
            else:
                # Bloqueia a aprovação desta RM específica e exibe o alerta
                st.error(
                    f"❌ **Aprovação Bloqueada:** Existem **{contagem_bloqueados}** item(ns) nesta RM sem "
                    f"correspondência na tabela 'api_materiais'. Ajuste o cadastro para liberar."
                )
                st.button(
                    f"🔒 RM {num_rm} Bloqueada ({contagem_bloqueados} pendências)", 
                    key=f"btn_bloqueado_{num_rm}", 
                    disabled=True, 
                    use_container_width=True
                )
else:
    st.info("Nenhuma requisição pendente (Status 1) foi localizada no banco.")
