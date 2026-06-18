import requests
import streamlit as st

def processar_e_enviar_api_externa(num_rm, df_itens_rm, token_autenticado):
    """
    Coloque toda a sua lógica gigante de integração aqui dentro!
    Este método varre os itens aprovados e faz os POSTs na API corporativa.
    """
    st.info(f"⚙️ Iniciando processamento em background para a RM {num_rm}...")
    
    total_enviados = 0
    total_erros = 0
    
    # Exemplo de loop varrendo a tabela consolidada
    for _, linha in df_itens_rm.iterrows():
        id_externo_api = linha.get("t_id")       # Seu ID Externo limpo
        codigo_mega_erp = linha.get("cod_mega")   # Código Mega
        quantidade = linha.get("qtd_solicitada")  # Qtd Solicitada
        
        # 🔹 MONTE SEU PAYLOAD DO JEITO QUE A API EXTERNA EXIGE:
        payload = {
            "idExterno": int(id_externo_api) if id_externo_api else None,
            "codigoItemMega": int(codigo_mega_erp) if codigo_mega_erp else None,
            "quantidade": float(quantidade)
        }
        
        # 🔹 EXEMPLO DE CHAMADA HTTP POST USANDO O TOKEN QUE CATCHAMOS NO LOGIN:
        # headers = {
        #     "Authorization": f"Bearer {token_autenticado}",
        #     "Content-Type": "application/json"
        # }
        # url_sua_api_externa = "https://azurewebsites.net"
        # response = requests.post(url_sua_api_externa, json=payload, headers=headers)
        
        total_enviados += 1  # Incremente conforme suas respostas HTTP 200/201
        
    # Retorna o resumo para a tela do Streamlit saber o que aconteceu
    return {
        "sucesso": True,
        "mensagens": f"🎉 RM {num_rm} processada! {total_enviados} itens integrados na API externa."
    }
