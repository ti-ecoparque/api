import streamlit as st
import requests
import json

# 1. Inicializa o estado global da sessão para navegação entre páginas
if "conectado" not in st.session_state:
    st.session_state.conectado = False
    st.session_state.token = None
    st.session_state.usuario_email = None

# 2. Carrega todos os dados fixos estruturais do arquivo config.json
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    URL_LOGIN = config["url_login"]
    ENTERPRISE_ID = config["enterpriseId"]
    # Captura a string de identificação que a API exige como obrigatória
    ENTERPRISE_ID_STRING = config.get("enterpriseIdString", str(ENTERPRISE_ID))
    IP_FIXO = config["ip"]
except Exception as e:
    st.error("Erro crítico: Não foi possível ler as configurações do arquivo 'config.json'.")
    st.stop()

# Interface visual da página de Login
st.title("🔐 Acesso ao Sistema Ecoparque")

if not st.session_state.conectado:
    # Solicita apenas e-mail e senha ao usuário
    email_input = st.text_input("E-mail corporativo", placeholder="exemplo@ecoparque.com.br")
    senha_input = st.text_input("Senha", type="password")

    if st.button("Entrar no Sistema", use_container_width=True):
        if email_input and senha_input:
            # 3. Monta o payload corrigido incluindo a chave EnterpriseIdString exigida pela API
            payload = {
                "email": email_input,
                "password": senha_input,
                "enterpriseId": int(ENTERPRISE_ID),
                "enterpriseIdString": str(ENTERPRISE_ID_STRING), # Campo adicionado para corrigir o Erro 400
                "ip": str(IP_FIXO)
            }

            with st.spinner("Autenticando..."):
                try:
                    headers = {"Content-Type": "application/json"}
                    response = requests.post(URL_LOGIN, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        dados_resposta = response.json()
                        
                        # Captura o Bearer Token do retorno da API
                        bearer_token = dados_resposta.get("token") or dados_resposta.get("accessToken")
                        
                        if bearer_token:
                            # SALVA EM MEMÓRIA VIVA DA SESSÃO
                            st.session_state.conectado = True
                            st.session_state.token = bearer_token
                            st.session_state.usuario_email = email_input
                            
                            st.success("Login efetuado com sucesso!")
                            st.rerun()  # Recarrega a página para atualizar o status e liberar o app
                        else:
                            st.error("Sucesso na API, mas o campo de Token não foi localizado no JSON retornado.")
                    else:
                        # Exibe os detalhes enviados e recebidos em caso de falha
                        st.error(f"Erro de Autenticação ({response.status_code})")
                        
                        with st.expander("Clique aqui para ver os detalhes técnicos do erro"):
                            st.write("**Dados que foram enviados para a API (Payload):**")
                            st.json(payload)
                            st.write("**Resposta retornada pelo servidor:**")
                            try:
                                st.json(response.json())
                            except:
                                st.code(response.text)
                        
                except Exception as erro:
                    st.error(f"Incapaz de conectar com o servidor da API: {erro}")
        else:
            st.warning("Preencha os campos de e-mail e senha.")
else:
    st.success(f"Conectado como: **{st.session_state.usuario_email}**")
    if st.button("Sair / Encerrar Sessão", type="primary"):
        st.session_state.conectado = False
        st.session_state.token = None
        st.session_state.usuario_email = None
        st.rerun()
