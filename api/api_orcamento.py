import requests
from datetime import datetime, timedelta


def listar_orcamento(token):
    url = "https://apiecoparque.azurewebsites.net/CompraOrcamento/CompraOrcamentoRefresh"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("❌ Erro ao buscar orçamentos:")
        print(response.text)
        return []

    data = response.json()

    print("🔍 DEBUG API:")
    print(type(data))

    # ✅ CORREÇÃO CERTA
    if isinstance(data, list):
        orcamentos = data
    elif isinstance(data, dict):
        orcamentos = data.get("orcamentos") or data.get("data") or []
    else:
        orcamentos = []

    print(f"✅ {len(orcamentos)} orçamentos carregados")

    return orcamentos

def itens_liberados(token):
    url = "https://apiecoparque.azurewebsites.net/CompraOrcamento/CompraRequisicaoItensLiberados"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "pessoaId": 40,
        "enderecoDeEntrega": "Area Fazenda Andrada, Br 277 0 - CASCAVEL (PR) - CEP: 85820-899"
    }

    response = requests.post(url, headers=headers, json=payload)

    print("🔍 STATUS:", response.status_code)

    if response.status_code != 200:
        print("❌ Erro:")
        print(response.text)
        return []

    data = response.json()

    print("🔍 RETORNO BRUTO:")
    print(data)

    # ✅ Aqui é o mais importante
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return data.get("data", [])

    return []


def criar_orcamento(token, itens_ids):
    url = "https://apiecoparque.azurewebsites.net/CompraOrcamento/CompraOrcamentoSave"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Data de encerramento (ex: +10 dias)
    encerramento = (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%dT00:00:00Z")

    payload = {
        "pessoaId": 40,
        "sequencial": 0,
        "freteTipoId": 2, # 2 = CIF
        "compraPedidoCondicaoPAGId": 2, # 2 = 28 Dias 
        "concluido": False,
        "disputa": False,
        "encerramento": encerramento,
        "enderecoDeEntrega": "Area Fazenda Andrada, Br 277 0 - CASCAVEL (PR) - CEP: 85820-899",
        "itensId": itens_ids,  # Lista de IDs
        "nome": "Junior",
        "observacao": ""
    }

    response = requests.post(url, headers=headers, json=payload)

    print("🔍 STATUS:", response.status_code)

    if response.status_code != 200:
        print("❌ Erro ao criar orçamento:")
        print(response.text)
        return None

    data = response.json()

    print("✅ Orçamento criado com sucesso!")
    print(f"ID: {data.get('compraOrcamentoId')}")
    print(f"Sequencial: {data.get('sequencial')}")

    return data


def buscar_itens_orcamento(token, orcamento_id):
    url = f"https://apiecoparque.azurewebsites.net/CompraOrcamento/CompraOrcamentoItens?id={orcamento_id}"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    print("🔍 STATUS:", response.status_code)

    if response.status_code != 200:
        print("❌ Erro ao buscar itens do orçamento:")
        print(response.text)
        return []

    data = response.json()

    print(f"✅ {len(data)} itens no orçamento")

    return data


def buscar_fornecedores_orcamento(token, orcamento_id):
    url = f"https://apiecoparque.azurewebsites.net/CompraOrcamento/CompraOrcamentoFornecedores?id={orcamento_id}"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    print("🔍 STATUS:", response.status_code)

    if response.status_code != 200:
        print("❌ Erro ao buscar fornecedores:")
        print(response.text)
        return []

    data = response.json()

    print(f"✅ {len(data)} fornecedores encontrados")

    return data

# pegar o GUID 
# fornecedores = buscar_fornecedores_orcamento(token, 4673)
#for fornecedor in fornecedores:
#    print("Fornecedor:", fornecedor["pessoa"])
#    print("ID:", fornecedor["pessoaId"])
#    print("GUID:", fornecedor["guid"])
#    print("Status:", forne
