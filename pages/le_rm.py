import streamlit as st
import pandas as pd
import unicodedata
import os
from supabase import create_client

# 1. CONFIGURAÇÃO E TRAVA DE SEGURANÇA (Primeiros comandos obrigatórios)
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("⚠️ Acesso negado. Por favor, faça login na tela inicial antes de continuar.")
    st.stop()

st.title("📋 Leitura e Tratamento de RMs")
st.write(f"Conectado como: **{st.session_state.get('usuario_email')}**")

# 2. CONEXÃO COM O SUPABASE
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Erro: Credenciais do Supabase não configuradas nos Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNÇÕES DE TRATAMENTO DE TEXTO E COLUNAS ---
def normalizar_texto(texto):
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ASCII', 'ignore').decode('utf-8')
    return texto.strip().lower()

def tratar_dados(df):
    df.columns = [normalizar_texto(col) for col in df.columns]
    df.rename(columns={
        'quantidade solicitada': 'QTD_SOLICITADA',
        'descricao do item':     'DESC_ITEM',
        'data de necessidade':   'DATA_NECESSIDADE',
        'usuario solicitante':   'USER_SOLICITACAO',
        'usuario de inclusao':   'COD_USER_MEGA',
        'especificacao':         'OBS_ITEM',
        'codigo do item':        'COD_MEGA',
        'codigo da solicitacao': 'COD_SOLICITACAO_MEGA',
        'nr. rm':                'N_RM',
        'sequencial do item':    'SEQ_ITEM'
    }, inplace=True)

    # Validação rígida de colunas obrigatórias exigidas pela tabela api_rm
    colunas_finais_obrigatorias = ['COD_SOLICITACAO_MEGA', 'DESC_ITEM', 'QTD_SOLICITADA', 'N_RM', 'SEQ_ITEM']

    for col in colunas_finais_obrigatorias:
        if col not in df.columns:
            st.error(f"❌ Coluna obrigatória não encontrada no arquivo: `{col}`")
            return None

    # Remove linhas que não possuem dados fundamentais
    df = df.dropna(subset=['DESC_ITEM', 'QTD_SOLICITADA', 'N_RM', 'SEQ_ITEM'])

    # 🔹 CORREÇÃO DE INTEIROS: Remove o ".0" limpando os identificadores e chaves do banco
    df['COD_SOLICITACAO_MEGA'] = pd.to_numeric(df['COD_SOLICITACAO_MEGA'], errors='coerce').astype('Int64')
    df['COD_MEGA'] = pd.to_numeric(df['COD_MEGA'], errors='coerce').astype('Int64')
    df['N_RM'] = pd.to_numeric(df['N_RM'], errors='coerce').astype('Int64')
    df['SEQ_ITEM'] = pd.to_numeric(df['SEQ_ITEM'], errors='coerce').astype('Int64')
    
    df['DESC_ITEM'] = df['DESC_ITEM'].astype(str).str.strip()
    df['QTD_SOLICITADA'] = pd.to_numeric(df['QTD_SOLICITADA'], errors='coerce')
    df = df[df['QTD_SOLICITADA'] > 0]

    return df

# --- INTERFACE DE ARRASTAR E SOLTAR ---
arquivos_enviados = st.file_uploader(
    "Arraste e solte seus arquivos da RM aqui (.xls ou .xlsx)", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

if arquivos_enviados:
    st.write(f"📂 **{len(arquivos_enviados)}** arquivo(s) carregado(s). Processando...")
    
    for arquivo in arquivos_enviados:
        st.subheader(f"📄 Arquivo: {arquivo.name}")
        
        try:
            df_bruto = pd.read_excel(arquivo)
            df_tratado = tratar_dados(df_bruto)
            
            if df_tratado is not None and not df_tratado.empty:
                st.success(f"✅ Dados tratados com sucesso! ({len(df_tratado)} linhas)")
                st.dataframe(df_tratado[['N_RM', 'SEQ_ITEM', 'DESC_ITEM', 'QTD_SOLICITADA']].head(5))
                
                # Botão para disparar a importação exclusiva desta planilha carregada
                if st.button(f"🚀 Importar {arquivo.name} para o Supabase", key=arquivo.name):
                    salvos = 0
                    ignorados = 0
                    
                    progresso = st.progress(0)
                    total_linhas = len(df_tratado)
                    
                    # Processa item por item para conseguir saltar duplicidades via Constraint de banco
                    for index, (_, linha) in enumerate(df_tratado.iterrows()):
                        data_nec = None
                        if 'DATA_NECESSIDADE' in linha and pd.notna(linha['DATA_NECESSIDADE']):
                            data_nec = str(linha['DATA_NECESSIDADE'])

                        registro = {
                            "cod_solicitacao_mega": int(linha["COD_SOLICITACAO_MEGA"]) if pd.notna(linha["COD_SOLICITACAO_MEGA"]) else None,
                            "desc_item": str(linha["DESC_ITEM"]),
                            "qtd_solicitada": float(linha["QTD_SOLICITADA"]),
                            "data_necessidade": data_nec,
                            "user_solicitacao": str(linha.get("USER_SOLICITACAO", "")) if pd.notna(linha.get("USER_SOLICITACAO")) else None,
                            "cod_user_mega": str(linha.get("COD_USER_MEGA", "")) if pd.notna(linha.get("COD_USER_MEGA")) else None,
                            "obs_item": str(linha.get("OBS_ITEM", "")) if pd.notna(linha.get("OBS_ITEM")) else None,
                            "cod_mega": int(linha["COD_MEGA"]) if pd.notna(linha["COD_MEGA"]) else None,
                            "n_rm": int(linha["N_RM"]),
                            "seq_item": int(linha["SEQ_ITEM"]),
                            "status_rm": 1, # Grava inicialmente com Status 1 (Pendente) conforme solicitado
                            "usuario_importacao": st.session_state.usuario_email
                        }
                        
                        try:
                            # Tenta inserir a linha única na tabela api_rm
                            supabase.table("api_rm").insert(registro).execute()
                            salvos += 1
                        except Exception as e:
                            # Código Postgres '23505' identifica barreira de Constraint (Duplicidade n_rm + seq_item)
                            if "23505" in str(e) or "unique_rm_item" in str(e):
                                ignorados += 1
                            else:
                                st.error(f"Erro inesperado de estrutura na linha {index}: {e}")
                        
                        progresso.progress((index + 1) / total_linhas)
                    
                    # Resumo informativo na interface para o operador
                    st.write("---")
                    st.success(f"📥 Processamento do lote finalizado!")
                    st.info(f"✔️ Novos itens salvos: **{salvos}**")
                    
                    if ignorados > 0:
                        st.warning(f"⚠️ Itens descartados por já existirem no banco: **{ignorados}**")
                        
        except Exception as e:
            st.error(f"Falha ao processar a leitura do Excel {arquivo.name}: {e}")
else:
    st.info("Aguardando o envio de planilhas para iniciar o processamento.")
