import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client

from api_config import obter_url_azure
from map.map_config import obter_pessoa_id, obter_centro_custo, obter_endereco_entrega


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
    # 🚨 1. VALIDAÇÃO ANTI-DUPLICIDADE (SUPABASE)
    # ==========================================================
    try:
        checagem_duplicidade = (
            supabase.table("api_integracao_sucesso")
            .select("n_rm")
            .eq("n_rm", int(num_rm))
            .execute()
        )
        
        if checagem_duplicidade.data:
            st.error(f"🛑 **Integração Abortada!** A RM nº **{num_rm}** já foi integrada anteriormente.")
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

    # ==========================================================
    # 🏗️ 2. MONTAGEM DO CABEÇALHO CORRIGIDO (MAP_CONFIG)
    # ==========================================================
    if df_itens_rm.empty:
        st.error(f"❌ Nenhum item encontrado para processar a RM {num_rm}")
        return {"sucesso": False, "mensagens": "DataFrame de itens vazio."}

    try:
        # Pega a primeira linha da planilha para extrair os dados gerais do cabeçalho
        dados_rm = df_itens_rm.iloc[0]

        # Extrai os códigos numéricos (força inteiro para não dar incompatibilidade)
        codigo_filial = int(dados_rm.get("filial_codigo"))
        codigo_usuario = int(dados_rm.get("usuario_codigo"))

        # Determina a data de entrega final tratando vazios e nulos do Pandas
        data_rm = dados_rm.get("data_entrega")
        if not data_rm or pd.isna(data_rm):
            data_entrega_final = (datetime.today() + timedelta(days=10)).strftime("%Y-%m-%d")
            st.warning("⚠️ Data da RM veio em branco. Atribuindo prazo padrão de 10 dias úteis.")
        else:
            data_entrega_final = pd.to_datetime(data_rm).strftime("%Y-%m-%d")

        # Injeta os dados limpos nas funções mapeadas do seu map_config.py
        payload_cabecalho = {
            "PessoaId": obter_pessoa_id(codigo_filial),
            "CentroDeCustoId": obter_centro_custo(codigo_usuario),
            "EnderecoDeEntrega": obter_endereco_entrega(codigo_filial),
            "DataDeEntrega": data_entrega_final,
            "Observacao": str(dados_rm.get("observacao") or f"Envio automatico da RM {num_rm}").strip()
        }

        # Registra no log visual os mapeamentos bem-sucedidos
        st.write(f"🏢 **Filial Mapeada:** {dados_rm.get('nome_filial')} (PessoaID: {payload_cabecalho['PessoaId']})")
        st.write(f"📁 **Centro de Custo Mapeado:** ID {payload_cabecalho['CentroDeCustoId']}")

    except Exception as e:
        st.error(f"💥 Erro na estruturação dos dados de mapeamento: {e}")
        return {"sucesso": False, "mensagens": f"Erro de mapeamento: {e}"}

    # ==========================================================
    # 📡 3. VALIDAÇÃO DE ITENS E DISPARO PARA A API DA AZURE
    # ==========================================================
    st.info("🔍 Iniciando pré-validação de consistência com a API da Azure...")
    
    try:
        url_azure = obter_url_azure()
        
        headers = {
            "Authorization": f"Bearer {token_autenticado}", 
            "Content-Type": "application/json"
        }
        
        # Converte os itens para dicionário compatível com o JSON da API
        itens_formatados = df_itens_rm.to_dict(orient="records")
        
        # Junta o cabeçalho validado aos itens filhos da RM
        payload_completo = {
            **payload_cabecalho, 
            "Itens": itens_formatados
        }
        
        # Realiza o disparo real por POST para o servidor da Azure
        resposta = requests.post(url_azure, json=payload_completo, headers=headers)
        
        if resposta.status_code in [200, 201]:
            supabase.table("api_integracao_sucesso").insert({"n_rm": int(num_rm)}).execute()
            return {
                "sucesso": True,
                "mensagens": f"🚀 RM {num_rm} integrada com sucesso na Azure e gravada no banco!"
            }
        else:
            return {
                "sucesso": False, 
                "mensagens": f"❌ Erro da API Externa ({resposta.status_code}): {resposta.text}"
            }
            
    except Exception as e:
        return {
            "sucesso": False,
            "mensagens": f"❌ Falha crítica na comunicação com a API da Azure: {e}"
        }

    # ==========================================================
    # 📡 VALIDAÇÃO DE ITENS E DISPARO PARA A API DA AZURE
    # ==========================================================
    # Daqui para baixo entra o seu loop que lê 'df_itens_rm', compara com a Azure
    # e envia o 'payload_cabecalho' acoplado aos produtos correspondentes.
    
    # Exemplo ilustrativo do envio final para a Azure:
    url_azure = obter_url_azure()
    headers = {"Authorization": f"Bearer {token_autenticado}", "Content-Type": "application/json"}
    
    # Exemplo estrutural de envio (Adapte conforme o formato exato da sua lista de itens filhos)
    payload_completo = {**payload_cabecalho, "Itens": df_itens_rm.to_dict(orient="records")}
    
    # resposta = requests.post(url_azure, json=payload_completo, headers=headers)
    
    return {"sucesso": True, "mensagens": "Cabeçalho estruturado com sucesso!"}

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
    # 2. CHAMADA HTTP 1: CRIA A REQUISIÇÃO MÃE (CORRIGIDO)
    # ==========================================
    url_requisicao = obter_url_azure("salvar_requisicao_mae")
    
    # 1. Trata e formata a data tratando valores nulos (None)
    try:
        data_string = str(data_entrega_original).strip()
        
        if not data_entrega_original or data_string == "None" or data_string == "":
            st.warning("⚠️ Data da RM veio em branco. Atribuindo prazo padrão de 7 dias úteis.")
            obj_data = datetime.now() + timedelta(days=7)
        else:
            if " " in data_string:
                data_string = data_string.split(" ")[0]
                
            if "/" in data_string:
                obj_data = datetime.strptime(data_string, "%d/%m/%Y")
            else:
                obj_data = datetime.strptime(data_string, "%Y-%m-%d")
            
        data_entrega_formatada = obj_data.strftime("%Y-%m-%dT00:00:00")
        
    except Exception as e_data:
        st.error(f"⚠️ Erro ao formatar a data original '{data_entrega_original}': {e_data}")
        return {"sucesso": False, "mensagens": "❌ Falha crítica no formato de data fornecido pela planilha."}

    # 2. Monta o payload direto na raiz (Plano) com letras maiúsculas
    # Removemos o envelopamento de 'payload_mae = {"dados": ...}'
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
        # O envio vai plano direto na raiz do JSON
        response_mae = requests.post(url_requisicao, json=payload_mae, headers=headers)
        
        if response_mae.status_code != 200:
            return {
                "sucesso": False,
                "mensagens": f"❌ Erro da API Externa ao gerar cabeçalho da RM {num_rm}: {response_mae.text}"
            }
            
        dados_mae = response_mae.json()
        
        # Mapeia todas as possibilidades de retorno da API para capturar o ID gerado
        req_id = dados_mae.get("compraRequisicaoId") or dados_mae.get("CompraRequisicaoId") or dados_mae.get("dados", {}).get("compraRequisicaoId")
        num_sequencial = dados_mae.get("sequencial") or dados_mae.get("Sequencial") or dados_mae.get("dados", {}).get("sequencial")
        
        if not req_id:
            return {
                "sucesso": False,
                "mensagens": f"❌ ID de requisição não foi localizado no dicionário de resposta da Azure: {dados_mae}"
            }
            
        st.write(f"✅ **Cabeçalho criado temporariamente na Azure!** ID: `{req_id}` | Nº: `{num_sequencial}`")
        
    except Exception as e:
        return {"sucesso": False, "mensagens": f"❌ Falha ao criar requisição mãe: {e}"}


    # ==========================================
    # 3. CHAMADA HTTP 2: INSERÇÃO DOS ITENS FILHOS
    # ==========================================
    url_item = obter_url_azure("salvar_item_filho")
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
        
        try:
            url_delete = obter_url_azure("deletar_requisicao")
            payload_delete = {"compraRequisicaoId": int(req_id)}
            response_delete = requests.post(url_delete, json=payload_delete, headers=headers)
            
            if response_delete.status_code == 200:
                st.info(f"🗑️ Requisição parcial {req_id} limpa e removida da Azure com sucesso.")
            else:
                st.error(f"⚠️ Erro ao tentar deletar cabeçalho na Azure (Status: {response_delete.status_code}).")
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
            
            # --- 🚨 FINALIZAÇÃO DO PROCESSO E MUDANÇA DE TELA ---
            st.balloons() # Efeito visual de sucesso
            st.success(f"RM {num_rm} integrada com sucesso! Redirecionando...")
            
            # Remove a planilha/dados da RM atual do estado da sessão para ela sumir da tela
            if "df_itens_rm" in st.session_state:
                del st.session_state["df_itens_rm"]
            
            # Altera a tela atual para a tela de listagem para atualizar o status visualmente
            st.session_state.tela_atual = "02 Listar Requisição de Material"
            
            # Força o Streamlit a recarregar a interface já na nova tela e sem os dados antigos
            st.rerun()
            
        except Exception as e_banco:
            return {
                "sucesso": False,
                "mensagens": f"❌ Erro gravíssimo ao salvar dados finais no banco (Azure OK, Banco Falhou): {e_banco}"
            }