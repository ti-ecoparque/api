import streamlit as st
import pandas as pd
import unicodedata

st.title("Importa RMs")
st.write(f"Conectado como: **{st.session_state.get('usuario_email')}**")

import streamlit as st

#Bloqueia quem não fez login no login.py
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("Acesso negado. Por favor, faça login na tela inicial antes de continuar.")
    st.stop() # Trava o script e não mostra mais nada abaixo