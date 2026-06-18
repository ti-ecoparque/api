import requests
import streamlit as st
import os
import sys
import pandas as pd
from supabase import create_client

# Garante o mapeamento de pastas para localizar o 'map_config' dentro do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Importa as funções auxiliares de mapeamento corporativo do seu map/map_config.py
from map.map_config import (
    obter_pessoa_id, 
    obter_nome_empresa, 
    obter_endereco_entrega, 
    obter_centro_custo_por_codigo
)

def processar_e_enviar_api_externa(num_rm, df_itens_rm, token_autenticado):
    """
    Função principal orquestradora: Recebe os dados validados do Streamlit,
    faz os mapeamentos, cria a Requisição mãe, salva os retornos de ID no Supabase 
    e insere os itens filhos na API Externa.
    """
    # Inicializa o cliente do Supabase localmente para salvar os retornos
    SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Como os cabeçalhos de Filial e Usuário são idênticos para toda a RM, pegamos da primeira linha
    primeira_linha = df_itens_rm.iloc[0]
    
    # Captura e força os códigos de mapeamento como inteiros para bater no dicionário
    cod_filial = int(primeira_linha.get("enterpriseId")) if pd.notna(primeira_linha.get("enterpriseId")) else 102
    cod_usuario_mega = int(primeira_linha.get("cod_user_mega")) if pd.notna(primeira_linha.get("cod_user_mega")) else None
    
    # Captura a data de entrega original e limpa frações de tempo
    data_entrega_original = str(primeira_linha.get("data_necessidade"))
    if data_entrega_original and " " in data_entrega_original:
        data_entrega_original = data_entrega_original.split(" ")[0] # Mantém apenas YYYY-MM-DD
    
    # 1. TRADUÇÃO DOS MAPS DINÂMICOS
    pessoa_id = obter_pessoa_id(cod_filial)
    nome_empresa = obter_nome_empresa(cod_filial)
    endereco_entrega = obter_endereco_entrega(cod_filial)
    centro_custo_id = obter_centro_custo_por_codigo(cod_usuario_mega) or 3 # Fallback Admin caso venha nulo
    
    if not pessoa_id or not nome_empresa:
        return {
            "sucesso": False,
            "mensagens": f"❌ Falha de Mapeamento: Filial {cod_filial} não encontrada no map_config.py."
        }

    st.write(f"🏢 **Filial Mapeada:** {nome_empresa} (PessoaID: {pessoa_id})")
    st.write(f"📁 **Centro de Custo Mapeado:** ID {centro_custo_id}")

    # ==========================================
    # 2. CHAMADA HTTP 1: CRIA A REQUISIÇÃO MÃE
    # ==========================================
    url_requisicao = "https://apiecoparque.azurewebsites.net/CompraRequisicao/CompraRequisicaoSave"
    
    headers = {
        "Authorization": f"Bearer {token_autenticado}",
        "Content-Type": "application/json"
    }
    
    payload_mae = {
        "compraRequisicaoId": 0,
        "sequencial": 0,
        "pessoaId": int(pessoa_id),
        "centroDeCustoId": int(centro_custo_id),
        "compraRequisicaoStatusId": 0,
        "dataDeEntrega": data_entrega_original,
        "observacao": f"Importação - {nome_empresa} - RM {num_rm}",
        "enderecoDeEntrega": str(endereco_entrega)
    }
    
    try:
        response_mae = requests.post(url_requisicao, json=payload_mae, headers=headers)
        
        if response_mae.status_code != 200:
            return {
                "sucesso": False,
                "mensagens": f"❌ Erro da API Externa ao gerar cabeçalho da RM {num_rm}: {response_mae.text}"
            }
            
        dados_mae = response_mae.json()
        req_id = dados_mae.get("compraRequisicaoId")
        num_sequencial = dados_mae.get("sequencial")
        
        st.write(f"✅ **Requisição Gerada na Azure!** ID: `{req_id}` | Nº: `{num_sequencial}`")
        
        # ==================================================================
        # HISTÓRICO DE RETORNO: SALVA OS IDS GERADOS PELA API NO SUPABASE
        # ==================================================================
        dados_historico = {
            "n_rm": int(num_rm),
            "compra_requisicao_id": int(req_id),
            "sequencial": int(num_sequencial),
            "usuario_integracao": str(st.session_state.usuario_email)
        }
        supabase.table("api_integracao_sucesso").insert(dados_historico).execute()
        st.write("💾 **Vínculo de IDs persistido com sucesso na tabela api_integracao_sucesso!**")
        
    except Exception as e:
        return {"sucesso": False, "mensagens": f"❌ Falha ao criar requisição mãe: {e}"}

    # ==========================================
    # 3. CHAMADA HTTP 2: INSERÇÃO DOS ITENS FILHOS
    # ==========================================
    url_item = "https://azurewebsites.net"
    total_itens_inseridos = 0
    itens_com_falha = 0
    
    barra_itens = st.progress(0)
    total_linhas = len(df_itens_rm)
    
    for idx, (_, linha_item) in enumerate(df_itens_rm.iterrows()):
        # Captura o t_id (ID do produto na API destino) que veio do PROCV da api_materiais
        id_externo_produto = linha_item.get("t_id")
        qtd = linha_item.get("qtd_solicitada")
        
        if pd.isna(id_externo_produto):
            st.warning(f"⚠️ Item Seq {linha_item.get('seq_item')} ignorado: Sem correspondência de ID Externo.")
            itens_com_falha += 1
            continue
            
        payload_filho = {
            "compraRequisicaoItemId": 0,
            "compraRequisicaoId": int(req_id),
            "produtoId": int(id_externo_produto), # Enviando o t_id correspondente
            "quantidade": int(float(qtd)),
            "marcaFixa": False
        }
        
        try:
            response_filho = requests.post(url_item, json=payload_filho, headers=headers)
            if response_filho.status_code == 200:
                total_itens_inseridos += 1
            else:
                st.error(f"❌ Falha ao inserir ProdutoID {id_externo_produto}: {response_filho.text}")
                itens_com_falha += 1
        except Exception as e:
            st.error(f"❌ Exceção de rede no ProdutoID {id_externo_produto}: {e}")
            itens_com_falha += 1
            
        barra_itens.progress((idx + 1) / total_linhas)

    # ==========================================
    # 4. RESUMO LOGÍSTICO FINAL
    # ==========================================
    if total_itens_inseridos > 0 and itens_com_falha == 0:
        return {
            "sucesso": True,
            "mensagens": f"🎉 Integração Concluída! RM {num_rm} integrada e salva. {total_itens_inseridos} itens sincronizados."
        }
    elif total_itens_inseridos > 0:
        return {
            "sucesso": True,
            "mensagens": f"⚠️ Integração Parcial: {total_itens_inseridos} itens sincronizados, mas {itens_com_falha} falharam."
        }
    else:
        return {
            "sucesso": False,
            "mensagens": "❌ Falha total: Nenhum item pôde ser inserido na requisição externa."
        }
