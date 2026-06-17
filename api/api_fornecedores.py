import requests

def buscar_precos_fornecedor(token, guid):
    url = f"https://apiecoparque.azurewebsites.net/CompraOrcamento/CompraOrcamentoFornecedorPrecos?guid={guid}"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    print("🔍 STATUS:", response.status_code)

    if response.status_code != 200:
        print("❌ Erro ao buscar preços:")
        print(response.text)
        return None

    data = response.json()

    print("✅ Dados do fornecedor carregados")
    print("Fornecedor:", data.get("fornecedor"))
    print("Orçamento:", data.get("compraOrcamentoId"))

    return data


def enviar_preco_fornecedor(token, guid, item_id, preco, marca=""):
    url = "https://apiecoparque.azurewebsites.net/CompraOrcamento/CompraOrcamentoFornecedorPrecoAdd"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "guid": guid,
        "compraOrcamentoItemId": item_id,
        "preco": preco,
        "marca": marca
    }

    response = requests.post(url, headers=headers, json=payload)

    print("🔍 STATUS:", response.status_code)

    if response.status_code != 200:
        print("❌ Erro ao enviar preço:")
        print(response.text)
        return False

    print("✅ Preço enviado com sucesso!")
    return True