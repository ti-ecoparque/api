import streamlit as st
import pandas as pd
import unicodedata

st.title("📋 Leitura e Tratamento de RMs")
st.write(f"Conectado como: **{st.session_state.get('usuario_email')}**")

import streamlit as st

# TRAVA DE SEGURANÇA: Bloqueia quem não fez login no login.py
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("⚠️ Acesso negado. Por favor, faça login na tela inicial antes de continuar.")
    st.stop() # Trava o script e não mostra mais nada abaixo

# A PARTIR DAQUI VEM O SEU CÓDIGO NORMAL DA RM...
st.title("📋 Leitura e Tratamento de RMs")

# ==========================================
# FUNÇÕES DE TRATAMENTO (SUA LÓGICA ATUAL)
# ==========================================

def normalizar_texto(texto):
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ASCII', 'ignore').decode('utf-8')
    return texto.strip().lower()

def tratar_dados(df):
    # 🔹 Normaliza colunas
    df.columns = [normalizar_texto(col) for col in df.columns]

    # 🔹 Rename conforme seu padrão original
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

    # VALIDAÇÕES IMPORTANTES
    colunas_obrigatorias = ['cod_solicitacao_mega', 'desc_item', 'qtd_solicitada']
    
    # Como as colunas foram normalizadas para minúsculo antes do rename, 
    # checamos os novos nomes mapeados (maiusculos)
    colunas_finais_obrigatorias = ['COD_SOLICITACAO_MEGA', 'DESC_ITEM', 'QTD_SOLICITADA']

    for col in colunas_finais_obrigatorias:
        if col not in df.columns:
            st.error(f"❌ ERRO: Coluna obrigatória não encontrada no arquivo: `{col}`")
            return None

    # Remove linhas vazias importantes
    df = df.dropna(subset=['DESC_ITEM', 'QTD_SOLICITADA'])

    # Corrige tipos
    df['DESC_ITEM'] = df['DESC_ITEM'].astype(str).str.strip()
    df['QTD_SOLICITADA'] = pd.to_numeric(df['QTD_SOLICITADA'], errors='coerce')

    # Remove quantidade inválida
    df = df[df['QTD_SOLICITADA'] > 0]

    return df

# ==========================================
# INTERFACE GRÁFICA E ARRASTAR/SOLTAR
# ==========================================

# Caixa para arrastar e soltar arquivos (Aceita múltiplos arquivos de uma vez)
arquivos_enviados = st.file_uploader(
    "Arraste e solte seus arquivos da RM aqui (.xls ou .xlsx)", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

# Se o usuário enviou um ou mais arquivos
if arquivos_enviados:
    st.write(f"📦 **{len(arquivos_enviados)}** arquivo(s) carregado(s). Processando...")
    
    # Itera sobre cada arquivo arrastado
    for arquivo in arquivos_enviados:
        st.subheader(f"📄 Arquivo: {arquivo.name}")
        
        try:
            # O pandas consegue ler diretamente o buffer em memória do Streamlit
            df_bruto = pd.read_excel(arquivo)
            
            # Executa o seu tratamento original
            df_tratado = tratar_dados(df_bruto)
            
            if df_tratado is not None:
                st.success(f"✅ Dados tratados com sucesso! ({len(df_tratado)} linhas válidas)")
                
                # Exibe uma prévia da tabela na tela do Streamlit para o usuário conferir
                st.dataframe(df_tratado[['COD_SOLICITACAO_MEGA', 'DESC_ITEM', 'QTD_SOLICITADA']].head(10))
                
                # Guarda o DataFrame tratado no estado da sessão caso queira usar em outra página/operação
                # Usamos o nome do arquivo como chave para separar se forem múltiplos
                if "rms_tratadas" not in st.session_state:
                    st.session_state.rms_tratadas = {}
                st.session_state.rms_tratadas[arquivo.name] = df_tratado
                
        except Exception as e:
            st.error(f"❌ Falha ao processar o arquivo {arquivo.name}: {e}")
            
else:
    st.info("Aguardando o envio de arquivos para iniciar o processamento.")
