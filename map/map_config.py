# MAP DE EMPRESAS (FILIAL → PESSOA ID)

MAP_EMPRESAS = {
    102: {
        "id": 40, # FABRICA 
        "nome": "ECOPARQUE BAIRROS INTEGRADOS LTDA F003", 
        "endereco": "Area Fazenda Andrada, Br 277 0 - CASCAVEL (PR) - CEP: 85820-899"
    },
    100: {
        "id": 28,
        "nome": "ECOPARQUE BAIRROS INTEGRADOS LTDA F001",
        "endereco": "Endereço da filial 100"
    },
    104: {
        "id": 39,
        "nome": "ECOPARQUE BAIRROS INTEGRADOS LTDA F002",
        "endereco": "Endereço da filial 104"
    }
}

# MAP DE CENTRO DE CUSTO (USUÁRIO → CENTRO DE CUSTO)

# 1 Fabrica - 2 Vendas - 3 Administração - 4 Estoque 
MAP_CENTRO_CUSTO = {
    55: {"id": 3, "descricao": "Administração"},        # Fabiana 
    53: {"id": 4, "descricao": "Estoque"},              # Paulo
    40: {"id": 3, "descricao": "Administração"},        # Adrielle
    21: {"id": 3, "descricao": "Administração"},         # Jonatha
    36: {"id": 3, "descricao": "Administração"} # PCP
}

# FUNÇÕES AUXILIARES

def obter_empresa(filial):
    """
    Retorna o objeto de empresa com base na filial.
    {
        "id": pessoaId,
        "nome": descricao
    }
    """
    return MAP_EMPRESAS.get(filial)


def obter_pessoa_id(filial):
    empresa = obter_empresa(filial)

    if empresa:
        return empresa["id"]

    return None


def obter_nome_empresa(filial):
    empresa = obter_empresa(filial)

    if empresa:
        return empresa["nome"]

    return None


def obter_centro_custo(usuario_codigo):

    if not usuario_codigo:
        return None

    return MAP_CENTRO_CUSTO.get(usuario_codigo, {}).get("id")


def obter_centro_custo_por_codigo(codigo_usuario):

    return MAP_CENTRO_CUSTO.get(codigo_usuario, {}).get("id")



def obter_centro_custo_descricao(usuario):
    if not usuario:
        return None

    usuario = str(usuario).lower().strip()

    cc = MAP_CENTRO_CUSTO.get(usuario)

    if cc:
        return cc["descricao"]

    return None


def obter_empresa(filial):
    return MAP_EMPRESAS.get(filial)


def obter_pessoa_id(filial):
    empresa = obter_empresa(filial)
    return empresa["id"] if empresa else None


def obter_nome_empresa(filial):
    empresa = obter_empresa(filial)
    return empresa["nome"] if empresa else None


def obter_endereco_entrega(filial):
    empresa = obter_empresa(filial)
    return empresa["endereco"] if empresa else None
