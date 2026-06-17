import streamlit as st
import requests
import json

# 1. Inicializa o estado global da sessão para navegação entre páginas
if "conectado" not in st.session_state:
    st.session_state.conectado = False
    st.session_state.token = None
    st.session_state.usuario_email = None

# 2. Função segura com cache para buscar o IP de internet real (evita quebrar a tela com HTML)
@st.cache_data(ttl=3600) # Guarda o IP por 1 hora para não ficar refazendo a requisição a cada clique
def buscar_ip_publico_real():
    try:
        # O icanhazip retorna APENAS o IP em formato de texto limpo
        resposta = requests.get("https://icanhazip.com", timeout=3)
        if resposta.status_code == 200:
            return resposta.text.strip()
    except Exception:
        pass
    
    # Se o serviço falhar, tenta o ipify com o formato JSON explícito para não trazer HTML
    try:
        resposta = requests.get("https://ipify.org", timeout=3)
        if resposta.status_code == 200:
            return resposta.json().get("ip")
    except Exception:
        pass
        
    # Último caso (Fallback local)
    return st.context.ip_address or "127.0.0.1"

# Executa a função para obter o IP limpo
ip_usuario = buscar_ip_publico_real()

# 3. Carrega os dados fixos estruturais do arquivo config.json
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    URL_LOGIN = config["url_login"]
    ENTERPRISE_ID = config["enterpriseId"]
except Exception as e:
    st.error("Erro crítico: Não foi possível ler o arquivo 'config.json'.")
    st.stop()

# Interface visual da página de Login
st.title("🔐 Acesso ao Sistema Ecoparque")

if not st.session_state.conectado:
    st.info(f"Seu IP de conexão detectado automaticamente: `{ip_usuario}`")

    # Solicita dados dinâmicos ao usuário (não salvos no código/Git)
    email_input = st.text_input("E-mail corporativo", placeholder="exemplo@ecoparque.com.br")
    senha_input = st.text_input("Senha", type="password")

    if st.button("Entrar no Sistema", use_container_width=True):
        if email_input and senha_input:
            # Monta o payload unindo dados fixos, digitados e o IP correto
            payload = {
                "email": email_input,
                "password": senha_input,
                "enterpriseId": ENTERPRISE_ID,
                "ip": ip_usuario
            }

            with st.spinner("Autenticando..."):
                try:
                    response = requests.post(URL_LOGIN, json=payload)
                    
                    if response.status_code == 200:
                        dados_resposta = response.json()
                        
                        # Captura o Bearer Token
                        bearer_token = dados_resposta.get("token") or dados_resposta.get("accessToken")
                        
                        if bearer_token:
                            # SALVA EM MEMÓRIA VIVA DA SESSÃO
                            st.session_state.conectado = True
                            st.session_state.token = bearer_token
                            st.session_state.usuario_email = email_input
                            
                            st.success("Login efetuado com sucesso!")
                            st.rerun()  # Recarrega a página para atualizar o status
                        else:
                            st.error("Sucesso na API, mas o campo de Token não foi localizado no JSON retornado.")
                    else:
                        st.error(f"Erro de Autenticação ({response.status_code}): Verifique seu e-mail e senha.")
                        
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
