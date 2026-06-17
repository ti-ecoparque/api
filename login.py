import streamlit as st
import requests
import json

# Configuração inicial da página (Deve ser a primeira linha do script)
st.set_page_config(page_title="Sistema Ecoparque", page_icon="🔐", layout="wide")

# 1. Inicializa o estado global da sessão se não existir
if "conectado" not in st.session_state:
    st.session_state.conectado = False
    st.session_state.token = None
    st.session_state.usuario_email = None

# 2. DEFINIÇÃO DAS PÁGINAS (Apontando para a nova pasta 'telas')
# st.Page define o arquivo físico, o título na barra lateral e o ícone
pagina_login = st.Page("login.py", title="Tela de Login", icon="🔑", default=True)
pagina_le_rm = st.Page("telas/le_RM.py", title="Leitura de RMs", icon="📋")
pagina_produtos = st.Page("telas/map_list_produtos.py", title="Lista de Produtos", icon="📦")


# ==========================================
# LÓGICA DE CONTROLE DE ACESSO (O SEGREDO)
# ==========================================
# Se o usuário NÃO está conectado, ele só enxerga a página de login
if not st.session_state.conectado:
    paginas_disponiveis = [pagina_login]
else:
    # Se ele ESTÁ conectado, liberamos as páginas de operação e ocultamos o login
    paginas_disponiveis = [pagina_le_rm, pagina_produtos]


# 3. CRIA A NAVEGAÇÃO DINÂMICA NA BARRA LATERAL
# O Streamlit só vai desenhar na barra lateral as páginas contidas na lista acima
pg = st.navigation(paginas_disponiveis)


# ==========================================
# INTERFACE E EXECUÇÃO DA TELA DE LOGIN
# ==========================================
# Se a página atual selecionada na navegação for o login.py, executa o bloco abaixo:
if pg == pagina_login:
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

    st.title("🔐 Acesso ao Sistema Ecoparque")

    # Solicita dados ao usuário
    email_input = st.text_input("E-mail corporativo", placeholder="exemplo@ecoparque.com.br")
    senha_input = st.text_input("Senha", type="password")

    if st.button("Entrar no Sistema", use_container_width=True):
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
                            # SALVA AS CREDENCIAIS NA MEMÓRIA DA SESSÃO
                            st.session_state.conectado = True
                            st.session_state.token = bearer_token
                            st.session_state.usuario_email = email_input
                            
                            st.success("Login efetuado com sucesso!")
                            st.rerun()  # Recarrega para aplicar a nova lista de páginas liberadas
                        else:
                            st.error("Sucesso na API, mas o Token não foi localizado no JSON retornado.")
                    else:
                        st.error(f"Erro de Autenticação ({response.status_code}): Verifique seu e-mail e senha.")
                except Exception as erro:
                    st.error(f"Incapaz de conectar com o servidor da API: {erro}")
        else:
            st.warning("Preencha os campos de e-mail e senha.")

else:
    # Se a página selecionada NÃO for a de login (ou seja, o usuário clicou em Leitura de RMs ou Produtos)
    # Adicionamos um botão de Logout no topo da barra lateral para conveniência
    st.sidebar.write(f"👤 **{st.session_state.usuario_email}**")
    if st.sidebar.button("🚪 Sair / Logout", use_container_width=True):
        st.session_state.conectado = False
        st.session_state.token = None
        st.session_state.usuario_email = None
        st.rerun()

    # Roda o código da subpágina selecionada (le_RM.py, map_list_produtos.py, etc.)
    pg.run()
