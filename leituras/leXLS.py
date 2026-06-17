import pandas as pd
import os
import shutil
import unicodedata


# NORMALIZA TEXTO
def normalizar_texto(texto):
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ASCII', 'ignore').decode('utf-8')
    return texto.strip().lower()


# BUSCAR ARQUIVO

def buscar_arquivos(pasta="XLS"):
    arquivos = []

    for arquivo in os.listdir(pasta):
        if arquivo.endswith((".xlsx", ".xls")):
            arquivos.append(os.path.join(pasta, arquivo))

    return arquivos


# LER EXCEL
def ler_excel(caminho):
    try:
        df = pd.read_excel(caminho)

        print("✅ Arquivo carregado")
        #print(df.head())

        return df

    except Exception as e:
        print(f"❌ Erro ao ler Excel: {e}")
        return None


# TRATAR DADOS
def tratar_dados(df):

    # 🔹 Normaliza colunas
    df.columns = [normalizar_texto(col) for col in df.columns]

    #print("\n📌 Colunas após normalização:")
    #print(df.columns)

    # 🔹 Rename conforme seu padrão
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

    #print("\n✅ Colunas finais:")
    #print(df.columns)

    # VALIDAÇÕES IMPORTANTES
    colunas_obrigatorias = ['COD_SOLICITACAO_MEGA', 'DESC_ITEM', 'QTD_SOLICITADA']

    for col in colunas_obrigatorias:
        if col not in df.columns:
            print(f"❌ ERRO: Coluna obrigatória não encontrada: {col}")
            return None

    # Remove linhas vazias importantes
    df = df.dropna(subset=['DESC_ITEM', 'QTD_SOLICITADA'])

    # Corrige tipos
    df['DESC_ITEM'] = df['DESC_ITEM'].astype(str).str.strip()
    df['QTD_SOLICITADA'] = pd.to_numeric(df['QTD_SOLICITADA'], errors='coerce')

    # Remove quantidade inválida
    df = df[df['QTD_SOLICITADA'] > 0]

    #print("\n✅ Dados tratados:")
    #print(df[['COD_SOLICITACAO_MEGA', 'DESC_ITEM', 'QTD_SOLICITADA']].head())

    return df

# MOVER ARQUIVO
def mover_arquivo(caminho, destino="PROCESSADOS"):

    if not os.path.exists(destino):
        os.makedirs(destino)

    nome = os.path.basename(caminho)
    novo_caminho = os.path.join(destino, nome)

    try:
        shutil.move(caminho, novo_caminho)
        print(f"✅ Arquivo movido para: {novo_caminho}")

    except Exception as e:
        print(f"❌ Erro ao mover arquivo: {e}")


# FUNÇÃO PRINCIPAL
def processar_excel():

    arquivos = buscar_arquivos()

    if not arquivos:
        print("❌ Nenhum arquivo encontrado")
        return []

    resultados = []

    for caminho in arquivos:

        df = ler_excel(caminho)

        if df is None:
            continue

        df = tratar_dados(df)

        if df is None:
            continue

        resultados.append((df, caminho))

    return resultados
