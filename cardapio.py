import pandas as pd
from collections import defaultdict

def processar_pagina(page):
    text = page.extract_text()
    tables = page.extract_tables()
    
    # Extrai todas as linhas de texto para identificar recessos
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Dicionário para mapear dias com recesso
    recesso_dias = {}
    current_day = None
    
    for line in lines:
        # Detecta linhas que começam com dias da semana
        if any(line.lower().startswith(weekday) for weekday in ['segunda', 'terça', 'quarta', 'quinta', 'sexta']):
            current_day = line
            recesso_dias[current_day] = False
        elif line == 'RECESSO' and current_day:
            recesso_dias[current_day] = True

    # Processa tabelas normalmente
    header0 = tables[0]
    day_indices = [1, 4, 7, 10, 13]
    day_names = []
    
    for idx in day_indices:
        part1 = header0[0][idx] if idx < len(header0[0]) else ""
        part2 = header0[1][idx] if idx < len(header0[1]) else ""
        combined = f"{part1} {part2}".strip()
        day_names.append(combined)
    
    if len(day_names) != 5:
        return None

    colunas_finais = ['Categoria'] + day_names

    # Processa o corpo das tabelas
    body_raw = [row for table in tables[1:] for row in table]
    clean_body = [row for row in body_raw if row and any(cell and cell.strip() for cell in row)]

    def adjust_row(row):
        row = row + [None] * (7 - len(row))
        if (not row[5] or row[5].strip() == "") and row[6] and row[6].strip() != "":
            row[5] = row[6]
        return row[:6]

    adjusted_body = [adjust_row(row) for row in clean_body if len(row) >= 6]
    df = pd.DataFrame(adjusted_body, columns=colunas_finais)
    df['Categoria'] = df['Categoria'].ffill()

    # Transforma para formato por dia
    df_t = df.set_index('Categoria').T.reset_index()
    df_t = df_t.rename(columns={'index': 'Dia'})

    # Aplica recessos
    for dia, is_recesso in recesso_dias.items():
        if is_recesso:
            # Encontra a linha correspondente ao dia de recesso
            mask = df_t['Dia'].str.contains(dia.split(',')[0], case=False, na=False)
            # Substitui todas as categorias por 'RECESSO'
            for col in df_t.columns[1:]:
                df_t.loc[mask, col] = 'RECESSO'

    agrupadas = defaultdict(list)
    for col in df_t.columns[1:]:
        agrupadas[col].append(col)

    df_agrupado = pd.DataFrame()
    df_agrupado['Dia'] = df_t['Dia']

    for categoria, col_list in agrupadas.items():
        if len(col_list) == 1:
            df_agrupado[categoria] = df_t[col_list[0]]
        else:
            df_agrupado[categoria] = df_t[col_list].apply(
                lambda row: ' e '.join(dict.fromkeys(filter(None, row))), axis=1
            )

    return df_agrupado