import streamlit as st
import requests
import json

# 1. CONFIGURAÇÃO DA PÁGINA (Sempre o primeiro comando)
st.set_page_config(page_title="Sistema Ecoparque", page_icon="🔐", layout="wide")

# 2. INICIALIZA O ESTADO DE LOGIN
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.token = None
    st.session_state.usuario_email = None

# 3. DEFINE AS PÁGINAS DO SISTEMA (Formato limpo e nativo do Streamlit)
pagina_login = st.Page("app.py", title="Tela de Login", icon="🔑", default=True)
pagina_le_rm = st.Page("pages/le_rm.py", title="Leitura de RMs", icon="📋")
#pagina_produtos = st.Page("pages/map_list_produtos.py", title="Lista de Produtos", icon="📦")

# 4. CONTROLE DE ACESSO SIMPLIFICADO
# Se não estiver logado, a lista só tem a tela de login. Se estiver, libera as outras.
if not st.session_state.logado:
    paginas_visiveis = [pagina_login]
else:
    paginas_visiveis = [pagina_le_rm, pagina_produtos]

# Cria a barra lateral de navegação automaticamente com as páginas permitidas
pg = st.navigation(paginas_visiveis)


# ==========================================
# LÓGICA DA TELA DE LOGIN
# ==========================================
if pg == pagina_login:
    # Carrega os dados fixos estruturais do arquivo config.json
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

                with st.spinner("Autenticando na API..."):
                    try:
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(URL_LOGIN, json=payload, headers=headers)
                        
                        if response.status_code == 200:
                            dados_resposta = response.json()
                            bearer_token = dados_resposta.get("token") or dados_resposta.get("accessToken")
                            
                            if bearer_token:
                                # Define o estado como logado e guarda o token obtido
                                st.session_state.logado = True
                                st.session_state.token = bearer_token
                                st.session_state.usuario_email = email_input
                                st.success("Login efetuado com sucesso!")
                                st.rerun() # Atualiza para redesenhar a barra lateral com as novas páginas
                            else:
                                st.error("Sucesso na API, mas o Token não foi localizado no JSON retornado.")
                        else:
                            st.error(f"Erro de Autenticação ({response.status_code}): Verifique seu e-mail e senha.")
                    except Exception as erro:
                        st.error(f"Incapaz de conectar com o servidor da API: {erro}")
            else:
                st.warning("Por favor, preencha os campos de e-mail e senha.")

# ==========================================
# SE O USUÁRIO CLICOU EM OUTRA PÁGINA (LOGADO)
# ==========================================
else:
    # Cria uma área personalizada no topo da barra lateral esquerda para exibir o usuário e o botão Sair
    with st.sidebar:
        st.write(f"👤 Conectado como: **{st.session_state.usuario_email}**")
        if st.button("🚪 Sair do Sistema", use_container_width=True, type="primary"):
            st.session_state.logado = False
            st.session_state.token = None
            st.session_state.usuario_email = None
            st.rerun()
        st.divider()

    # Roda nativamente o arquivo correspondente selecionado (pages/le_rm.py, etc.)
    pg.run()
