import streamlit as st
import requests
import json

# Configuração da página (DEVE ser o primeiro comando do script)
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


# --- DEFINIÇÃO DO FLUXO DE NAVEGAÇÃO ---

# 1. Define a página de login (o próprio arquivo login.py atual atuando como função)
def tela_login():
    st.markdown("<h2 style='text-align: center;'>🔑 Acesso Restrito - Ecoparque</h2>", unsafe_allow_html=True)
    
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

# 2. Mapeamento das páginas internas (Aqui você define os nomes bonitos sem mudar o arquivo físico)
pagina_01 = st.Page("pages/le_rm.py", title="01 - Ler Requisição de Material", icon="📄")
pagina_02 = st.Page("pages/lista_rm.py", title="02 Listar Requisição de Material", icon="📋")
pagina_03 = st.Page("pages/importar_rm.py", title="03 Importar RM - API", icon="📥")

# Função de logout para exibir no menu lateral
def fazer_logout():
    st.session_state.logado = False
    st.session_state.token = None
    st.session_state.usuario_email = None
    st.rerun()

pagina_logout = st.Page(fazer_logout, title="Sair do Sistema", icon="🚪")


# 3. LÓGICA DE EXIBIÇÃO DO MENU BASEADO NO LOGIN
if not st.session_state.logado:
    # Se NÃO está logado, a única página acessível e visível é o formulário de login
    pg = st.navigation([st.Page(tela_login, title="Login", icon="🔐")], position="hidden")
else:
    # Se ESTÁ logado, exibe as páginas internas com os títulos customizados e o logout
    pg = st.navigation({
        "Menu Principal": [pagina_01, pagina_02, pagina_03],
        "Configurações": [pagina_logout]
    })
    
    # Exibe o e-mail do usuário no topo da barra lateral para validação visual
    st.sidebar.markdown(f"👤 **Conectado como:**\n\n`{st.session_state.usuario_email}`")
    st.sidebar.markdown("---")

# Executa a página selecionada pelo usuário no menu
pg.run()
