import streamlit as st
import requests
import json
from streamlit.web.server.websocket_headers import _get_websocket_headers

# Função para capturar o IP automático do usuário
def get_client_ip():
    headers = _get_websocket_headers()
    if headers:
        x_forwarded_for = headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return headers.get("Remote-Addr", "127.0.0.1")
    return "127.0.0.1"

# 1. Inicializa as variáveis globais de sessão se não existirem
if "conectado" not in st.session_state:
    st.session_state.conectado = False
    st.session_state.token = None
    st.session_state.usuario_email = None

# 2. Carrega os dados estruturais fixos do seu arquivo config.json (Sem dados sensíveis)
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    URL_LOGIN = config["url_login"]
    ENTERPRISE_ID = config["enterpriseId"]
except Exception as e:
    st.error("Erro ao carregar o arquivo config.json")
    st.stop()

# Interface Gráfica de Login
st.title("🔐 Acesso ao Sistema Ecoparque")

if not st.session_state.conectado:
    # Captura o IP de forma dinâmica
    user_ip = get_client_ip()
    st.info(f"Seu IP de conexão detectado: `{user_ip}`")

    # Formulário de entrada de dados do usuário
    email_input = st.text_input("E-mail corporativo", placeholder="seu_email@ecoparque.com.br")
    senha_input = st.text_input("Senha", type="password")

    if st.button("Entrar no Sistema"):
        if email_input and senha_input:
            # Monta o payload exatamente como sua API externa espera, incluindo o IP dinâmico
            payload = {
                "email": email_input,
                "password": senha_input,
                "enterpriseId": ENTERPRISE_ID,
                "ip": user_ip  # IP capturado automaticamente
            }

            with st.spinner("Autenticando na API externa..."):
                try:
                    response = requests.post(URL_LOGIN, json=payload)
                    
                    if response.status_code == 200:
                        resposta_data = response.json()
                        
                        # Extrai o token enviado pela sua API (ajuste a chave 'token' se o nome for diferente no seu JSON de retorno)
                        bearer_token = resposta_data.get("token") or resposta_data.get("accessToken")
                        
                        if bearer_token:
                            # 3. SALVA TUDO NA SESSÃO DO STREAMLIT (Memória viva do navegador)
                            st.session_state.conectado = True
                            st.session_state.token = bearer_token
                            st.session_state.usuario_email = email_input
                            
                            st.success("Autenticação realizada com sucesso!")
                            st.rerun()  # Recarrega a página já com o estado de conectado
                        else:
                            st.error("Login aceito, mas o Bearer Token não foi encontrado na resposta da API.")
                    else:
                        st.error(f"Falha na autenticação ({response.status_code}): Verifique suas credenciais.")
                        
                except Exception as error:
                    st.error(f"Erro crítico ao tentar conectar com a API: {error}")
        else:
            st.warning("Por favor, preencha todos os campos.")
else:
    st.success(f"Você já está autenticado como **{st.session_state.usuario_email}**!")
    if st.button("Efetuar Logout"):
        st.session_state.conectado = False
        st.session_state.token = None
        st.session_state.usuario_email = None
        st.rerun()
