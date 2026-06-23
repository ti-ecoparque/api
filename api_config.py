# api_config.py

# URL Base do servidor da Azure
AZURE_BASE_URL = "https://apiecoparque.azurewebsites.net"

# Dicionário com o mapa completo de endpoints do sistema Ecoparque
ENDPOINTS_AZURE = {
    "login": f"{AZURE_BASE_URL}/Login/Autenticar", # Exemplo de rota caso use futuramente
    "listar_produtos": f"{AZURE_BASE_URL}/Produto/ProdutoList",
    "salvar_requisicao_mae": f"{AZURE_BASE_URL}/CompraRequisicao/CompraRequisicaoSave",
    "salvar_item_filho": f"{AZURE_BASE_URL}/CompraRequisicao/CompraRequisicaoItemSave",
    "deletar_requisicao": f"{AZURE_BASE_URL}/CompraRequisicao/CompraRequisicaoDelete"
}

def obter_url_azure(chave_endpoint):
    """
    Função auxiliar para capturar a URL de forma segura.
    Evita que o sistema quebre caso digite o nome do endpoint errado.
    """
    url = ENDPOINTS_AZURE.get(chave_endpoint)
    if not url:
        raise ValueError(f"❌ Erro de Configuração: O endpoint '{chave_endpoint}' não existe no api_config.py")
    return url
