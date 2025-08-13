import pandas as pd
import pdfplumber
import log_cardapio as log

logger = log.setup_logger()

def corrigir_day_names(day_names):
    """
    Remove duplicatas e valores vazios da lista de dias
    """
    seen = set()
    unique_days = []
    
    for day in day_names:
        day_clean = str(day).strip() if day else ""
        
        if day_clean and day_clean not in seen:
            seen.add(day_clean)
            unique_days.append(day_clean)
    
    logger.debug(f"Dias únicos após limpeza: {unique_days}")
    return unique_days

def processar_pagina(page, page_num):
    try:
        logger.info(f"\n{'='*50}\nIniciando processamento da página {page_num}\n{'='*50}")
        
        # Extração do texto
        text = page.extract_text() or ""
        logger.info(f"Texto extraído: {text[:9999]}...")

        # Extração de tabelas
        tables = page.extract_tables() or []
        logger.info(f"Encontradas {len(tables)} tabelas na página {page_num}")

        # --- INÍCIO DA MODIFICAÇÃO PARA PÁGINA 3 ---
        header0 = tables[0] if tables else []
        day_indices = [1, 4, 7, 10, 13]  # Ajuste conforme a estrutura real da página 3
        day_names_raw = []

        logger.info("Processando cabeçalhos dos dias...")
        for idx in day_indices:
            # Verificação robusta para estruturas irregulares
            part1 = header0[0][idx] if (len(header0) > 0 and idx < len(header0[0])) else ""
            part2 = header0[1][idx] if (len(header0) > 1 and idx < len(header0[1])) else ""
            day_name = f"{part1} {part2}".strip()
            
            if day_name:  # Ignora dias vazios
                day_names_raw.append(day_name)
                logger.debug(f"Índice {idx}: {day_name}")
            else:
                logger.warning(f"Dia vazio/ausente no índice {idx}")

        # CORREÇÃO PRINCIPAL - FUNÇÃO EXISTENTE (mantém igual)
        day_names = corrigir_day_names(day_names_raw)
        # --- FIM DA MODIFICAÇÃO PARA PÁGINA 3 ---

        
        if len(day_names) == 0:
            logger.error("Nenhum dia válido encontrado!")
            return pd.DataFrame()

        # Processamento do corpo da tabela
        logger.info("Processando corpo da tabela...")
        body_raw = [row for table in tables[1:] for row in table if row]
        clean_body = [row for row in body_raw if any(cell and str(cell).strip() for cell in row)]
        logger.info(f"Encontradas {len(clean_body)} linhas de dados")

        def adjust_row(row):
            # Ajusta para o número correto de colunas baseado nos dias válidos
            target_length = len(day_names) + 1  # +1 para a coluna categoria
            row = list(row) + [None] * (target_length - len(row))
            return row[:target_length]

        adjusted_body = [adjust_row(row) for row in clean_body if len(row) >= 2]
        
        # Cria DataFrame com colunas corretas
        columns = ['Categoria'] + day_names
        df = pd.DataFrame(adjusted_body, columns=columns)
        df['Categoria'] = df['Categoria'].ffill().str.strip()
        
        # Remove linhas vazias
        df = df[df['Categoria'].notna() & (df['Categoria'] != '')]
        logger.info(f"DataFrame criado com {len(df)} linhas")

        if df.empty:
            logger.warning("DataFrame vazio após limpeza!")
            return pd.DataFrame()

        if df['Categoria'].duplicated().any():
            logger.warning(f"Categorias duplicadas encontradas na página {page_num}")
            logger.debug(f"Categorias: {df['Categoria'].unique()}")

        # Formato longo
        df_melted = df.melt(id_vars=['Categoria'], var_name='Dia', value_name='Refeição')
        df_melted['Refeição'] = df_melted['Refeição'].apply(lambda x: x.strip() if isinstance(x, str) else x)
        df_melted = df_melted.dropna(subset=['Refeição'])
        
        # Remove refeições vazias
        df_melted = df_melted[df_melted['Refeição'].str.strip() != '']

        if df_melted.empty:
            logger.warning("DataFrame melted vazio!")
            return pd.DataFrame()

        # Agrupa sem reordenar
        df_agrupado = (
            df_melted
            .groupby(['Dia', 'Categoria'], sort=False)
            .agg({'Refeição': lambda x: ' e '.join(filter(None, x))})
            .reset_index()
        ).drop_duplicates(subset=['Dia', 'Categoria'])

        if df_agrupado.empty:
            logger.warning("DataFrame agrupado vazio!")
            return pd.DataFrame()

        # Pivot e reordena conforme day_names
        logger.info("Criando pivot...")
        df_t = df_agrupado.pivot(index='Dia', columns='Categoria', values='Refeição').reset_index()
        df_t.columns.name = None
        
        # CORREÇÃO: Só aplica ordenação categórica se temos dias únicos válidos
        try:
            # Verifica quais dias realmente existem no DataFrame
            dias_existentes = [dia for dia in day_names if dia in df_t['Dia'].values]
            
            if len(dias_existentes) > 1 and len(set(dias_existentes)) == len(dias_existentes):
                df_t['__ordem__'] = pd.Categorical(df_t['Dia'], categories=dias_existentes, ordered=True)
                df_t = df_t.sort_values('__ordem__').drop(columns='__ordem__').reset_index(drop=True)
                logger.info("Ordenação categórica aplicada com sucesso")
            else:
                logger.info("Pulando ordenação categórica - dias insuficientes ou duplicados")
        except Exception as e:
            logger.warning(f"Erro na ordenação categórica: {e}. Continuando sem ordenação.")

        # Metadados
        df_t['Pagina'] = page_num
        df_t['Arquivo'] = "cardapio_junho.pdf"

        logger.info(f"Processamento da página {page_num} concluído com sucesso!")
        return df_t

    except Exception as e:
        logger.error(f"ERRO no processamento da página {page_num}: {str(e)}", exc_info=True)
        return pd.DataFrame()


def processar_pdf(pdf_path):
    """
    Função principal mantida igual, só usando pdfplumber
    """
    try:
        logger.info(f"\n{'#'*60}\nINICIANDO PROCESSAMENTO DO ARQUIVO: {pdf_path}\n{'#'*60}")
        
        dfs = []
        with pdfplumber.open(pdf_path) as pdf:
            total_paginas = len(pdf.pages)
            logger.info(f"Total de páginas no PDF: {total_paginas}")
            
            for i, page in enumerate(pdf.pages, 1):
                df_pag = processar_pagina(page, i)
                if not df_pag.empty:
                    # Verifica e remove duplicatas antes de adicionar à lista
                    if df_pag.duplicated().any():
                        logger.warning(f"Removendo linhas duplicadas da página {i}")
                        df_pag = df_pag.drop_duplicates()
                    dfs.append(df_pag)
                else:
                    logger.warning(f"Página {i} retornou DataFrame vazio")
        
        if dfs:
            # Concatena garantindo índices únicos
            df_final = pd.concat(dfs, ignore_index=True)

            import re
            # Extrai o número do dia do texto (ex.: "terça-feira, 3 de junho de 2025" -> 3)
            try:
                df_final['__dia_num__'] = df_final['Dia'].str.extract(r'(\d{1,2})').astype(int)
                # Ordena pelo número do dia, mantendo a ordem estável de cada página
                df_final = (
                    df_final
                    .sort_values(by='__dia_num__', kind='stable')
                    .drop(columns='__dia_num__')
                    .reset_index(drop=True)
                )
            except Exception as e:
                logger.warning(f"Erro na ordenação final: {e}. Mantendo ordem original.")

            logger.info(f"\n{'#'*60}\nPROCESSAMENTO CONCLUÍDO!")
            logger.info(f"Total de páginas processadas: {len(dfs)}")
            logger.info(f"Total de registros: {len(df_final)}")
            logger.info(f"{'#'*60}")
            logger.info("\nResumo do DataFrame Final:\n" + str(df_final.head()))
            
            return df_final
        else:
            logger.error("Nenhum dado válido foi processado!")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Falha no processamento do PDF: {str(e)}", exc_info=True)
        return pd.DataFrame()

# Exemplo de uso
if __name__ == "__main__":
    df_resultado = processar_pdf("cardapio_junho.pdf")
    if not df_resultado.empty:
        print("Processamento concluído com sucesso!")
        df_resultado.to_csv("cardapio_processado.csv", index=False)
    else:
        print("Falha no processamento!")