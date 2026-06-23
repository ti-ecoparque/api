import requests
import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

# Importa o mapa de configuração centralizado das URLs da Azure
from api_config import obter_url_azure

def processar_e_enviar_api_externa(num_rm, df_itens_rm, token_autenticado):
    """
    Função principal orquestradora:
    - Valida duplicidade no Supabase
    - Pré-valida os produtos na Azure
    - Cria o cabeçalho mãe (com tratamento de data nula)
    - Insere os itens filhos com regra de tudo ou nada (Rollback)
    - Persiste o histórico completo no Supabase
    """
    # Inicializa o cliente do Supabase localmente para salvar os retornos
    SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ==========================================================
    # 🚨 1. VALIDAÇÃO ANTI-DUPLICIDADE (SUPABASE)
    # ==========================================================
    st.info("🔍 Verificando se a RM já foi integrada anteriormente no banco de dados...")
    try:
        # Busca se já existe um registro com o número desta RM na tabela
        checagem_duplicidade = (
            supabase.table("api_integracao_sucesso")
            .select("n_rm")
            .eq("n_rm", int(num_rm))
            .execute()
        )
        
        # Se retornar dados, significa que a RM já foi integrada
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
    url_produtos_azure = obter_url_azure("listar_produtos")
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
            p_id = prod.get("produtoId") or prod.get("id") or prod.get("ProdutoId")
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
            "mensagens": f"❌ A RM possui {len(itens_invalidos_na_azure)} item(ns) inválido(s) na Azure."
        }

    st.success("✔️ Pré-validação concluída! 100% dos produtos constam como válidos e ativos na Azure.")

    # ==========================================================
    # 🏗️ 2. MONTAGEM DO CABEÇALHO CORRIGIDO (MAP_CONFIG)
    # ==========================================================
    primeira_linha = df_itens_rm.iloc[0]
    cod_filial = int(primeira_linha.get("enterpriseId")) if pd.notna(primeira_linha.get("enterpriseId")) else 102
    cod_usuario_mega = int(primeira_linha.get("cod_user_mega")) if pd.notna(primeira_linha.get("cod_user_mega")) else None
    data_entrega_original = primeira_linha.get("data_necessidade")
    
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
    
    if not pessoa_id or not nome_empresa:
        return {
            "sucesso": False,
            "mensagens": f"❌ Falha de Mapeamento: Filial {cod_filial} não encontrada no map_config.py."
        }

    st.write(f"🏢 **Filial Mapeada:** {nome_empresa} (PessoaID: {pessoa_id})")
    st.write(f"📁 **Centro de Custo Mapeado:** ID {centro_custo_id}")

        # Tratamento e formatação estrita da data contra valores nulos ou fusos horários
    try:
        data_string = str(data_entrega_original).strip()
        
        # 1. Se a data vier vazia, 'None' ou em branco da planilha
        if not data_entrega_original or data_string == "None" or data_string == "":
            st.warning("⚠️ Data da RM veio em branco. Atribuindo prazo padrão de 7 dias úteis.")
            obj_data = datetime.now() + timedelta(days=7)
        else:
            # 2. Usa o Pandas para converter inteligentemente qualquer formato (ISO, BR, etc)
            # O errors='coerce' transforma valores inválidos em NaT (Not a Time)
            data_convertida = pd.to_datetime(data_entrega_original, errors='coerce')
            
            # Se o pandas falhar na conversão, assume a trava de segurança de 7 dias
            if pd.isna(data_convertida):
                st.warning("⚠️ Formato de data não reconhecido. Atribuindo prazo padrão de 7 dias úteis.")
                obj_data = datetime.now() + timedelta(days=7)
            else:
                obj_data = data_convertida

        # 3. Formata no padrão estrito limpo que a Azure exige (AAAA-MM-DDTHH:mm:ss)
        data_entrega_formatada = obj_data.strftime("%Y-%m-%dT00:00:00")
        
    except Exception as e_data:
        st.error(f"⚠️ Erro ao formatar a data original '{data_entrega_original}': {e_data}")
        return {"sucesso": False, "mensagens": "❌ Falha crítica no formato de data fornecido pela planilha."}


    # CHAMADA HTTP: CRIA A REQUISIÇÃO MÃE NA AZURE
    url_requisicao = obter_url_azure("salvar_requisicao_mae")
    
    payload_mae = {
        "CompraRequisicaoId": 0,
        "Sequencial": 0,
        "PessoaId": int(pessoa_id),
        "CentroDeCustoId": int(centro_custo_id),
        "CompraRequisicaoStatusId": 0,
        "DataDeEntrega": data_entrega_formatada,
        "Observacao": f"Importação - {nome_empresa} - RM {num_rm}",
        "EnderecoDeEntrega": str(endereco_entrega)
    }

    try:
        response_mae = requests.post(url_requisicao, json=payload_mae, headers=headers)
        
        if response_mae.status_code != 200:
            return {
                "sucesso": False,
                "mensagens": f"❌ Erro da API Externa ao gerar cabeçalho da RM {num_rm}: {response_mae.text}"
            }
            
        dados_mae = response_mae.json()
        req_id = dados_mae.get("compraRequisicaoId") or dados_mae.get("CompraRequisicaoId") or dados_mae.get("dados", {}).get("compraRequisicaoId")
        num_sequencial = dados_mae.get("sequencial") or dados_mae.get("Sequencial") or dados_mae.get("dados", {}).get("sequencial")
        
        if not req_id:
            return {
                "sucesso": False,
                "mensagens": f"❌ ID de requisição não localizado na resposta da Azure: {dados_mae}"
            }
            
        st.write(f"✅ **Cabeçalho criado temporariamente na Azure!** ID: `{req_id}` | Nº: `{num_sequencial}`")
        
    except Exception as e:
        return {"sucesso": False, "mensagens": f"❌ Falha ao criar requisição mãe: {e}"}


    # ==========================================================
    # 📥 3. CHAMADA HTTP 2: INSERÇÃO DOS ITENS FILHOS
    # ==========================================================
    url_item = obter_url_azure("salvar_item_filho")
    total_linhas = len(df_itens_rm)
    
    # Lista temporária em memória para acumular os registros de sucesso
    itens_para_salvar_no_banco = []
    processo_falhou = False
    motivo_falha = ""
    
    barra_itens = st.progress(0)
    
    for idx, (_, linha_item) in enumerate(df_itens_rm.iterrows()):
        id_externo_produto = linha_item.get("t_id")
        qtd = linha_item.get("qtd_solicitada")
        qtd_final = int(float(qtd))
        
        # Payload com a primeira letra Maiúscula conforme padrão exigido pelo C#/.NET
        payload_filho = {
            "CompraRequisicaoItemId": 0,
            "CompraRequisicaoId": int(req_id),
            "ProdutoId": int(id_externo_produto),
            "Quantidade": qtd_final,
            "MarcaFixa": False
        }
        
        try:
            response_filho = requests.post(url_item, json=payload_filho, headers=headers)
            
            if response_filho.status_code == 200:
                st.write(f"🔹 Item {idx+1}/{total_linhas} enviado à Azure → ProdutoID: {id_externo_produto}")
                
                # Guarda o item na lista temporária para o Supabase
                itens_para_salvar_no_banco.append({
                    "compra_requisicao_id": int(req_id),
                    "produto_id": int(id_externo_produto),
                    "quantidade": qtd_final
                })
            else:
                processo_falhou = True
                motivo_falha = f"Erro da Azure no ProdutoID {id_externo_produto}: {response_filho.text}"
                break  # Aborta o loop na primeira falha para acionar o Rollback
                
        except Exception as e:
            processo_falhou = True
            motivo_falha = f"Exceção de rede no ProdutoID {id_externo_produto}: {e}"
            break  # Aborta se a conexão de internet cair
            
        barra_itens.progress((idx + 1) / total_linhas)


    # ==========================================================
    # 🔄 4. APLICAÇÃO DA REGRA TUDO OU NADA (ROLLBACK / COMMIT)
    # ==========================================================
    if processo_falhou:
        st.warning("⚠️ **Falha detectada durante o envio dos itens! Ativando Rollback...**")
        st.error(f"Motivo do cancelamento: {motivo_falha}")
        
        # Executa o Rollback limpando o cabeçalho gerado na Azure
        try:
            url_delete = obter_url_azure("deletar_requisicao")
            payload_delete = {"compraRequisicaoId": int(req_id)}
            
            response_delete = requests.post(url_delete, json=payload_delete, headers=headers)
            
            if response_delete.status_code == 200:
                st.info(f"🗑️ Requisição parcial {req_id} removida da Azure com sucesso.")
            else:
                st.error(f"⚠️ Erro ao deletar cabeçalho na Azure (Status: {response_delete.status_code}).")
                
        except Exception as err_del:
            st.error(f"Erro de rede ao tentar limpar a requisição na Azure: {err_del}")
            
        return {
            "sucesso": False,
            "mensagens": f"❌ Integração cancelada e revertida. Nenhum dado foi salvo no Supabase."
        }
        
    else:
        # Se chegou aqui, 100% dos itens entraram na Azure com sucesso! (COMMIT)
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
                
            # 3. Atualiza o status na tabela api_rm
            supabase.table("api_rm").update({"status_rm": 3}).eq("id", int(num_rm)).execute()
            
            # Retorna os dados para a tela exibir no pop-up
            return {
                "sucesso": True,
                "req_id": req_id,
                "sequencial": num_sequencial,
                "total_itens": len(itens_para_salvar_no_banco),
                "mensagens": f"🎉 RM {num_rm} integrada com sucesso!"
            }
            
        except Exception as e_banco:
            return {
                "sucesso": False,
                "mensagens": f"❌ Erro ao salvar dados finais no banco: {e_banco}"
            }
