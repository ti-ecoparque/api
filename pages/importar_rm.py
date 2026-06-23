import streamlit as st
import pandas as pd
import os
from supabase import create_client

# Importa a lógica isolada do seu novo arquivo de envio
from api_set_rm import processar_e_enviar_api_externa

# 1. CONFIGURAÇÃO E TRAVA DE SEGURANÇA
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


# ==========================================================
# 🚨 1. DEFINIÇÃO DA JANELA MODAL DE SUCESSO (SEM BALÕES)
# ==========================================================
@st.dialog("Integração Concluída com Sucesso")
def mostrar_resumo_sucesso(num_rm, req_id, sequencial, total_itens):
    st.write(f"A Requisição de Material **Nº {num_rm}** foi totalmente processada.")
    
    # Exibe o resumo logístico de forma limpa, direta e corporativa
    st.info(
        f"**Resumo Logístico:**\n"
        f"* 🆔 **ID gerado na Azure:** `{req_id}`\n"
        f"* 🔢 **Nº Sequencial Azure:** `{sequencial}`\n"
        f"* 📦 **Total de Itens Sincronizados:** `{total_itens} item(ns)`\n\n"
        f"Os registros foram salvos no Supabase e o status da RM mudou para integrado."
    )
    
    st.write("Clique no botão abaixo para concluir e retornar à listagem.")
    
    # O fluxo permanece travado aqui até o clique manual do operador
    if st.button("Ok, Finalizar Processo", type="primary", use_container_width=True):
        # Descarrega os dados antigos da tela para limpar o formulário
        if "df_itens_rm" in st.session_state:
            del st.session_state["df_itens_rm"]
            
        # Altera a aba de visualização do menu lateral para a listagem
        st.session_state.tela_atual = "02 Listar Requisição de Material"
        st.rerun()


st.divider()

# REQUISIÇÃO DOS DADOS (STATUS_RM == 2)
with st.spinner("Buscando requisições aprovadas na fila (Status 2)..."):
    try:
        resposta_rm = supabase.table("api_rm").select("*").eq("status_rm", 2).execute()
        dados_fila = resposta_rm.data
        
        resposta_materiais = supabase.table("api_materiais").select("m_coditem, t_id, t_item").execute()
        dados_materiais = resposta_materiais.data
    except Exception as e:
        st.error(f"Erro ao consultar a fila no Supabase: {e}")
        dados_fila, dados_materiais = [], []
        
# PROCESSAMENTO DOS DADOS COM PANDAS
if dados_fila:
    df_rm = pd.DataFrame(dados_fila)
    df_mat = pd.DataFrame(dados_materiais)
    
    df_rm["cod_mega"] = pd.to_numeric(df_rm["cod_mega"], errors="coerce").astype("Int64")
    if not df_mat.empty:
        df_mat["m_coditem"] = pd.to_numeric(df_mat["m_coditem"], errors="coerce").astype("Int64")
        
    if not df_mat.empty:
        df_consolidado = pd.merge(df_rm, df_mat, left_on="cod_mega", right_on="m_coditem", how="left")
    else:
        df_consolidado = df_rm.copy()
        df_consolidado["t_id"] = None
        df_consolidado["t_item"] = None

    if "data_necessidade" in df_consolidado.columns:
        df_consolidado["data_necessidade_br"] = pd.to_datetime(df_consolidado["data_necessidade"], errors="coerce").dt.strftime("%d/%m/%Y")
    else:
        df_consolidado["data_necessidade_br"] = "---"

    rms_na_fila = sorted(df_consolidado["n_rm"].dropna().unique())
    st.info(f"📦 Encontrada(s) **{len(rms_na_fila)}** RM(s) aguardando envio para a API externa.")
    
    for num_rm in rms_na_fila:
        df_rm_atual = df_consolidado[df_consolidado["n_rm"] == num_rm]
        
        with st.expander(f"📋 RM Nº {num_rm} — Fila de Envio ({len(df_rm_atual)} itens)", expanded=True):
            
            linhas_tabela = []
            for _, linha in df_rm_atual.iterrows():
                id_externo_limpo = int(linha["t_id"]) if pd.notna(linha.get("t_id")) else "---"
                
                linhas_tabela.append({
                    "Seq": linha.get("seq_item"),
                    "Código Mega": linha.get("cod_mega"),
                    "Descrição do Item": linha.get("desc_item"),
                    "ID Externo": id_externo_limpo,
                    "Descrição Externa": linha.get("t_item") if pd.notna(linha.get("t_item")) else "---",
                    "Qtd Solicitada": linha.get("qtd_solicitada"),
                    "Data da RM": linha.get("data_necessidade_br")
                })
                
            df_exibicao = pd.DataFrame(linhas_tabela).sort_values(by="Seq")
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
            
            # BOTÃO DE EXECUÇÃO DA INTEGRAÇÃO
            if st.button(f"⚡ Enviar e Integrar RM {num_rm} na API Externa", key=f"btn_integrar_{num_rm}", use_container_width=True, type="primary"):
                with st.spinner("Processando chamadas HTTP externas da subrotina..."):
                    
                    # Puxa o Bearer token que salvamos lá na sessão do login.py
                    token_sessao = st.session_state.get("token")
                    
                    # EXECUTA A LÓGICA ISOLADA DO ARQUIVO API_SET_RM.PY
                    resultado = processar_e_enviar_api_externa(num_rm, df_rm_atual, token_sessao)
                    
                    # 🔍 2. NOVO TRATAMENTO COM DISPARO DA JANELA MODAL
                    if resultado.get("sucesso"):
                        # Dispara a janela modal de sucesso passando as chaves retornadas
                        mostrar_resumo_sucesso(
                            num_rm=num_rm,
                            req_id=resultado["req_id"],
                            sequencial=resultado["sequencial"],
                            total_itens=resultado["total_itens"]
                        )
                    else:
                        # Se a integração falhar, abre um alerta vermelho com o motivo
                        st.error("❌ **Falha na Integração da RM!**")
                        st.warning(resultado.get("mensagens"))
                        
                        if "detalhes" in resultado:
                            with st.expander("Inspecionar erro técnico completo do servidor"):
                                st.code(resultado.get("detalhes"))

else:
    st.info("✨ Tudo em dia! Nenhuma requisição com Status 2 localizada na fila de integração.")
