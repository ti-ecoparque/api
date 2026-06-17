import streamlit as st
import requests
import json

# Configuração da página (Primeiro comando)
st.set_page_config(page_title="Sistema Ecoparque", page_icon="🔐", layout="wide")

# Inicializa o estado de login se não existir
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.token = None
    st.session_state.usuario_email = None

# Carrega os dados estruturais do arquivo config.json
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    URL_LOGIN = config["url_login"]
    ENTERPRISE_ID = config["enterpriseId"]
    ENTERPRISE_ID_STRING = config.get("enterpriseIdString", str(ENTERPRISE_ID))
    IP_FIXO = config["ip"]
except Exception as e:
    st.error("Erro crítico: Não foi possível ler as configurações do arquivo 'config.json'.")
    st.stop()

st.markdown("<h2 style='text-align: center;'>🔑 Acesso Restrito - Ecoparque</h2>", unsafe_allow_html=True)

# Se JÁ ESTÁ logado, mostra mensagem de sucesso
if st.session_state.logado:
    st.success(f"Você já está autenticado como **{st.session_state.usuario_email}**!")
    st.info("Utilize o menu na barra lateral esquerda para navegar entre as telas.")
    
    if st.button("🚪 Sair do Sistema / Logout", type="primary"):
        st.session_state.logado = False
        st.session_state.token = None
        st.session_state.usuario_email = None
        st.rerun()

# Se NÃO está logado, exibe o formulário de login
else:
    with st.form("form_login", clear_on_submit=False):
        st.write("Insira suas credenciais corporativas para acessar o painel:")
        email_input = st.text_input("E-mail")
        senha_input = st.text_input("Senha", type="password")
        botao_entrar = st.form_submit_button("Entrar no Painel", use_container_width=True)
        
        if botao_entrar:
            if email_input and senha_input:
                payload = {
                    "email": email_input,
                    "password": senha_input,
                    "enterpriseId": int(ENTERPRISE_ID),
                    "enterpriseIdString": str(ENTERPRISE_ID_STRING),
                    "ip": str(IP_FIXO)
                }

                with st.spinner("Autenticando..."):
                    try:
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(URL_LOGIN, json=payload, headers=headers)
                        
                        if response.status_code == 200:
                            dados_resposta = response.json()
                            bearer_token = dados_resposta.get("token") or dados_resposta.get("accessToken")
                            
                            if bearer_token:
                                st.session_state.logado = True
                                st.session_state.token = bearer_token
                                st.session_state.usuario_email = email_input
                                st.success("Login efetuado com sucesso!")
                                st.rerun()
                            else:
                                st.error("Token não localizado na resposta da API.")
                        else:
                            st.error(f"Erro ({response.status_code}): Credenciais incorretas.")
                    except Exception as erro:
                        st.error(f"Erro de conexão: {erro}")
            else:
                st.warning("Preencha e-mail e senha.")
