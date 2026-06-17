import requests
from datetime import datetime

def listar_produtos(token):

    url = "https://apiecoparque.azurewebsites.net/Produto/ProdutoList"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("Erro ao buscar produtos:")
        print(response.text)
        return None

    data = response.json()

    produtos = data.get("produtos", [])

    print(f"{len(produtos)} produtos carregados")

    return produtos


def criar_requisicao(
    token,
    codigo_solicitacao,
    pessoa_id,
    centro_custo_id,
    nome_empresa,
    endereco,
    data_entrega
):

    url = "https://apiecoparque.azurewebsites.net/CompraRequisicao/CompraRequisicaoSave"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "compraRequisicaoId": 0,
        "sequencial": 0,
        "pessoaId": pessoa_id,
        "centroDeCustoId": centro_custo_id,
        "compraRequisicaoStatusId": 0,
        "dataDeEntrega": data_entrega,
        "observacao": f"Importação - {nome_empresa} - {codigo_solicitacao}",
        "enderecoDeEntrega": endereco
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"❌ Erro ao criar requisição {codigo_solicitacao}")
        print(response.text)
        return None, None

    dados = response.json()

    req_id = dados["compraRequisicaoId"]
    sequencial = dados.get("sequencial")

    print(f"✅ Criada → ID: {req_id} | Nº: {sequencial}")

    return req_id, sequencial


def inserir_item(token, req_id, produto_id, qtd):

    url = "https://apiecoparque.azurewebsites.net/CompraRequisicao/CompraRequisicaoItemSave"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "compraRequisicaoItemId": 0,
        "compraRequisicaoId": req_id,
        "produtoId": produto_id,
        "quantidade": int(qtd), 
        "marcaFixa": False
    }

    try:
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            print(f"❌ Erro ao inserir item ProdutoID: {produto_id}")
            print(response.text)
            return False

        data = response.json()

        item_id = data.get("compraRequisicaoItemId")

        print(
            f"✅ Item inserido → ItemID: {item_id} | "
            f"ProdutoID: {produto_id} | QTD: {qtd}"
        )

        return True

    except Exception as e:
        print(f"❌ Exception ao inserir item {produto_id}: {e}")
        return False
