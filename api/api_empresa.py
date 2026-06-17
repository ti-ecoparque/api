import requests

def listar_empresas(token):

    url = "https://apiecoparque.azurewebsites.net/Pessoa/PessoaTiposList?roleName=Empresa"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("❌ Erro ao buscar empresas:")
        print(response.text)
        return []

    data = response.json()

    print("📊 Retorno da API Empresas:")
    print(data)

    # ✅ tentativa padrão
    if isinstance(data, list):
        empresas = data
    else:
        empresas = data.get("data", data)

    print(f"✅ {len(empresas)} empresas carregadas")

    return empresas

def encontrar_empresa_id(empresas, nome_busca):

    nome_busca = nome_busca.lower()

    for emp in empresas:
        nome_api = str(emp.get("nome", emp.get("descricao", ""))).lower()

        if nome_busca in nome_api:
            return emp.get("pessoaId")

    return None
