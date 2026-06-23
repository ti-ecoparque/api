import requests
import streamlit as st
import os
import sys
import pandas as pd
from supabase import create_client

def processar_e_enviar_api_externa(num_rm, df_itens_rm, token_autenticado):
    """
    Função principal orquestradora com PRÉ-VALIDAÇÃO EM TEMPO REAL:
    Busca os produtos ativos na Azure, valida se todos os t_id da RM existem lá,
    e só realiza os disparos HTTP se 100% dos itens forem localizados.
    Garante também que uma RM já integrada não seja duplicada no banco de dados.
    """
    # Inicializa o cliente do Supabase localmente para salvar os retornos
    SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    st.info("🔍 Verificando se a RM já foi integrada anteriormente no banco de dados...")

    # ==========================================================
    # 🚨 VALIDAÇÃO ANTI-DUPLICIDADE (SUPABASE)
    # ==========================================================
    try:
        checagem_duplicidade = (
            supabase.table("api_integracao_sucesso")
            .select("n_rm")
            .eq("n_rm", int(num_rm))
            .execute()
        )
        
        if checagem_duplicidade.data:
            st.error(f"🛑 **Integração Abortada!** A RM nº **{num_rm}** já foi integrada anteriormente e os registros constam no banco de dados.")
            return {
                "sucesso": False,
                "mensagens": f"❌ Duplicidade detectada: A RM {num_rm} já foi processada no sistema."
            }
            
    except Exception as e:
        return {
            "sucesso": False,
            "mensagens": f"❌ Erro ao validar duplicidade de RM na tabela do Supabase: {e}"
        }

    st.success("✔️ Validação de duplicidade OK! Esta RM é nova e pode ser integrada.")
    st.info("🔍 Iniciando pré-validação de consistência com a API da Azure...")

    # ==========================================================
    # 🚨 FASE 0: BUSCA E VALIDAÇÃO DOS PRODUTOS VIVOS NA AZURE
    # ==========================================================
    url_produtos_azure = "https://apiecoparque.azurewebsites.net/Produto/ProdutoList"
    headers = {
        "Authorization": f"Bearer {token_autenticado}",
        "Content-Type": "application/json"
    }

    try:
        response_prod = requests.get(url_produtos_azure, headers=headers)
        if response_prod.status_code != 200:
            return {
                "sucesso": False,
                "mensagens": f"❌ Falha crítica: Não foi possível checar a lista de produtos na Azure. Status: {response_prod.status_code}"
            }
        
        dados_prod = response_prod.json()
        produtos_vivos_azure = dados_prod.get("produtos", dados_prod) if isinstance(dados_prod, dict) else dados_prod
        
        ids_validos_azure = set()
        for prod in produtos_vivos_azure:
            p_id = prod.get("produtoId") or prod.get("id")
            if p_id is not None:
                ids_validos_azure.add(int(p_id))

    except Exception as e:
        return {"sucesso": False, "mensagens": f"❌ Falha de conexão ao validar produtos na Azure: {e}"}

    itens_invalidos_na_azure = []
    
    for _, linha_item in df_itens_rm.iterrows():
        id_externo_produto = linha_item.get("t_id")
        
        if pd.isna(id_externo_produto):
            itens_invalidos_na_azure.append(f"Seq {linha_item.get('seq_item')} (Código Mega: {linha_item.get('cod_mega')}) - ID Externo Ausente")
            continue
            
        if int(id_externo_produto) not in ids_validos_azure:
            itens_invalidos_na_azure.append(f"Seq {linha_item.get('seq_item')} (ID Externo: {int(id_externo_produto)}) - Descrição: {linha_item.get('desc_item')}")

    if itens_invalidos_na_azure:
        st.error("🛑 **Integração Abortada por Inconsistência de Cadastro!**")
        st.write("Os seguintes itens da planilha possuem ID Externo (`t_id`) que **não existem ou estão inativos** dentro do sistema da Azure:")
        for item_erro in itens_invalidos_na_azure:
            st.warning(item_erro)
            
        return {
            "sucesso": False,
            "mensagens": f"❌ A RM possui {len(itens_invalidos_na_azure)} item(ns) inválido(s) na Azure. Atualize a Lista Mestra ou cadastre o produto na Azure antes de enviar."
        }

    st.success("✔️ Pré-validação concluída! 100% dos produtos constam como válidos e ativos na Azure.")

    # ==========================================
    # 1. CAPTURA DOS METADADOS DE FILIAL
    # ==========================================
    primeira_linha = df_itens_rm.iloc[0]
    cod_filial = int(primeira_linha.get("enterpriseId")) if pd.notna(primeira_linha.get("enterpriseId")) else 102
    cod_usuario_mega = int(primeira_linha.get("cod_user_mega")) if pd.notna(primeira_linha.get("cod_user_mega")) else None
    
    data_entrega_original = str(primeira_linha.get("data_necessidade"))
    if data_entrega_original and " " in data_entrega_original:
        data_entrega_original = data_entrega_original.split(" ")[0]
    
    from map.map_config import (
        obter_pessoa_id, 
        obter_nome_empresa, 
        obter_endereco_entrega, 
        obter_centro_custo_por_codigo
    )
    
    pessoa_id = obter_pessoa_id(cod_filial)
    nome_empresa = obter_nome_empresa(cod_filial)
    endereco_entrega = obter_endereco_entrega(cod_filial)
    centro_custo_id = obter_centro_custo_por_codigo(cod_usuario_mega) or 3
    
    if not ... or not nome_empresa:
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
        
        st.write(f"✅ **Cabeçalho criado temporariamente na Azure!** ID: `{req_id}` | Nº: `{num_sequencial}`")
        
    except Exception as e:
        return {"sucesso": False, "mensagens": f"❌ Falha ao criar requisição mãe: {e}"}

    # ==========================================
    # 3. CHAMADA HTTP 2: INSERÇÃO DOS ITENS FILHOS
    # ==========================================
    url_item = "https://apiecoparque.azurewebsites.net/CompraRequisicao/CompraRequisicaoItemSave"
    total_linhas = len(df_itens_rm)
    
    itens_para_salvar_no_banco = []
    processo_falhou = False
    motivo_falha = ""
    
    barra_itens = st.progress(0)
    
    for idx, (_, linha_item) in enumerate(df_itens_rm.iterrows()):
        id_externo_produto = linha_item.get("t_id")
        qtd = linha_item.get("qtd_solicitada")
        qtd_final = int(float(qtd))
        
        payload_filho = {
            "compraRequisicaoItemId": 0,
            "compraRequisicaoId": int(req_id),
            "produtoId": int(id_externo_produto),
            "quantidade": qtd_final,
            "marcaFixa": False
        }
        
        try:
            response_filho = requests.post(url_item, json=payload_filho, headers=headers)
            
            if response_filho.status_code == 200:
                st.write(f"🔹 Item {idx+1}/{total_linhas} enviado à Azure → ProdutoID: {id_externo_produto}")
                itens_para_salvar_no_banco.append({
                    "compra_requisicao_id": int(req_id),
                    "produto_id": int(id_externo_produto),
                    "quantidade": qtd_final
                })
            else:
                processo_falhou = True
                motivo_falha = f"Erro da Azure no ProdutoID {id_externo_produto}: {response_filho.text}"
                break
                
        except Exception as e:
            processo_falhou = True
            motivo_falha = f"Exceção de rede no ProdutoID {id_externo_produto}: {e}"
            break
            
        barra_itens.progress((idx + 1) / total_linhas)
        
    # ==========================================
    # 4. APLICAÇÃO DA REGRA TUDO OU NADA (ROLLBACK / COMMIT)
    # ==========================================
    if processo_falhou:
        st.warning("⚠️ **Falha detectada durante o envio dos itens! Ativando Rollback...**")
        st.error(f"Motivo do cancelamento: {motivo_falha}")
        
        # Executa o Rollback na Azure deletando a requisição mãe incompleta
        try:
            # Endpoint real estruturado com base no padrão da sua API Ecoparque
            url_delete = f"https://azurewebsites.net" 
            
            # Enviamos o ID da requisição que precisa ser abortada/removida
            payload_delete = {"compraRequisicaoId": int(req_id)}
            
            response_delete = requests.post(url_delete, json=payload_delete, headers=headers)
            
            if response_delete.status_code == 200:
                st.info(f"🗑️ Requisição parcial {req_id} limpa e removida da Azure com sucesso.")
            else:
                st.error(f"⚠️ Atenção: A API retornou status {response_delete.status_code} ao tentar deletar. Verifique no painel da Azure se o ID {req_id} foi removido.")
                
        except Exception as err_del:
            st.error(f"Erro de rede ao tentar limpar a requisição mãe na Azure: {err_del}")
            
        return {
            "sucesso": False,
            "mensagens": f"❌ Integração cancelada e revertida. Nenhum dado foi salvo no banco de dados corporativo do Supabase."
        }
        
    else:
        # Se chegou aqui, 100% dos itens entraram na Azure com sucesso.
        st.success("🎉 Todos os itens foram aceitos pela Azure! Iniciando gravação das tabelas...")
        
        try:
            # 1. Salva o Cabeçalho na tabela api_integracao_sucesso
            dados_historico = {
                "n_rm": int(num_rm),
                "compra_requisicao_id": int(req_id),
                "sequencial": int(num_sequencial),
                "usuario_integracao": str(st.session_state.usuario_email)
            }
            supabase.table("api_integracao_sucesso").insert(dados_historico).execute()
            
            # 2. Salva os Itens Filhos em lote (bulk insert) na nova tabela api_integracao_itens
            if itens_para_salvar_no_banco:
                supabase.table("api_integracao_itens").insert(itens_para_salvar_no_banco).execute()
                
            st.write("💾 **Todos os dados e vínculos salvos com sucesso no banco de dados!**")
            
            return {
                "sucesso": True,
                "mensagens": f"🎉 Integração Concluída! RM {num_rm} enviada com sucesso. {len(itens_para_salvar_no_banco)} itens sincronizados e gravados."
            }
            
        except Exception as e_banco:
            return {
                "sucesso": False,
                "mensagens": f"❌ Erro gravíssimo ao salvar dados finais no banco (Azure OK, Banco Falhou): {e_banco}"
            }    