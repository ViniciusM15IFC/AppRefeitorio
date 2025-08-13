import pandas as pd
import pdfplumber
import log_cardapio as log

logger = log.setup_logger()

def processar_pagina(page, page_num):
    try:
        logger.info(f"\n{'='*50}\nIniciando processamento da página {page_num}\n{'='*50}")
        
        # Extração do texto
        text = page.extract_text() or ""
        logger.info(f"Texto extraído (primeiros 200 chars): {text[:200]}...")

        # Extração de tabelas
        tables = page.extract_tables() or []
        logger.info(f"Encontradas {len(tables)} tabelas na página {page_num}")

        # Processamento de recessos
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        recesso_dias = {}
        current_day = None
        weekdays = ['segunda', 'terça', 'quarta', 'quinta', 'sexta']

        logger.info("Procurando por dias de recesso...")
        for line in lines:
            if any(line.lower().split()[0].lower() == wd for wd in weekdays):
                current_day = line
                recesso_dias[current_day] = False
                logger.info(f"Encontrado dia: {current_day}")
            elif line.upper() == 'RECESSO' and current_day:
                recesso_dias[current_day] = True
                logger.info(f"Marcado recesso para: {current_day}")

        # Processamento das tabelas
        if not tables:
            logger.warning("Nenhuma tabela encontrada na página!")
            return pd.DataFrame()
            
        if len(tables[0]) < 2:
            logger.warning("Estrutura de tabela inesperada - menos de 2 linhas no header")
            return pd.DataFrame()

        header0 = tables[0]
        day_indices = [1, 4, 7, 10, 13]
        day_names = []

        logger.info("Processando cabeçalhos dos dias...")
        for idx in day_indices:
            part1 = header0[0][idx] if idx < len(header0[0]) else ""
            part2 = header0[1][idx] if idx < len(header0[1]) else ""
            day_name = f"{part1} {part2}".strip()
            day_names.append(day_name)
            logger.debug(f"Índice {idx}: {day_name}")

        if len(day_names) != 5:
            logger.error(f"Número incorreto de dias encontrados: {len(day_names)}")
            return pd.DataFrame()

        # Processamento do corpo da tabela
        logger.info("Processando corpo da tabela...")
        body_raw = [row for table in tables[1:] for row in table if row]
        clean_body = [row for row in body_raw if any(cell and str(cell).strip() for cell in row)]
        logger.info(f"Encontradas {len(clean_body)} linhas de dados")

        def adjust_row(row):
            row = list(row) + [None] * (7 - len(row))
            if (not row[5] or str(row[5]).strip() == "") and row[6] and str(row[6]).strip():
                row[5] = row[6]
            return row[:6]

        adjusted_body = [adjust_row(row) for row in clean_body if len(row) >= 6]
        df = pd.DataFrame(adjusted_body, columns=['Categoria'] + day_names)
        df['Categoria'] = df['Categoria'].ffill().str.strip()
        logger.info(f"DataFrame criado com {len(df)} linhas")

        if df['Categoria'].duplicated().any():
            logger.warning(f"Categorias duplicadas encontradas na página {page_num}")
            logger.debug(f"Categorias: {df['Categoria'].unique()}")

        # Formato longo
        df_melted = df.melt(id_vars=['Categoria'], var_name='Dia', value_name='Refeição')
        df_melted['Refeição'] = df_melted['Refeição'].apply(lambda x: x.strip() if isinstance(x, str) else x)
        df_melted = df_melted.dropna(subset=['Refeição'])

        # Agrupa sem reordenar
        df_agrupado = (
            df_melted
            .groupby(['Dia', 'Categoria'], sort=False)
            .agg(lambda x: ' e '.join(filter(None, x)))
            .reset_index()
        ).drop_duplicates(subset=['Dia', 'Categoria'])

        # Pivot e reordena conforme day_names
        logger.info(f"Pivot Modificado")
        df_t = df_agrupado.pivot(index='Dia', columns='Categoria', values='Refeição').reset_index()
        df_t.columns.name = None
        df_t['__ordem__'] = pd.Categorical(df_t['Dia'], categories=day_names, ordered=True)
        df_t = df_t.sort_values('__ordem__').drop(columns='__ordem__').reset_index(drop=True)

        # Aplicação de recessos
        logger.info("Aplicando recessos...")
        for dia, is_recesso in recesso_dias.items():
            if is_recesso:
                dia_base = dia.split(',')[0].strip().lower()
                mask = df_t['Dia'].str.strip().str.lower().str.startswith(dia_base)
                for col in df_t.columns[1:]:
                    df_t.loc[mask, col] = 'RECESSO'
                logger.info(f"Aplicado RECESSO para {dia}")

        # Metadados
        df_t['Pagina'] = page_num
        df_t['Arquivo'] = "cardapio_junho.pdf"

        logger.info(f"Processamento da página {page_num} concluído com sucesso!")
        return df_t

    except Exception as e:
        logger.error(f"ERRO no processamento da página {page_num}: {str(e)}", exc_info=True)
        return pd.DataFrame()


def processar_pdf(pdf_path):
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
            df_final['__dia_num__'] = df_final['Dia'].str.extract(r'(\d{1,2})').astype(int)

            # Ordena pelo número do dia, mantendo a ordem estável de cada página
            df_final = (
                df_final
                .sort_values(by='__dia_num__', kind='stable')
                .drop(columns='__dia_num__')
                .reset_index(drop=True)
            )

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
