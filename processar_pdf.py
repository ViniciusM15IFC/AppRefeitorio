import pandas as pd
from collections import defaultdict

def processar_pagina(
    page,
    *,
    transpose: bool = True,
    num_linhas_cabecalho: int = 2,
    col_indices_dias: list[int] = None,
    fill: str = None,
    aplicar_recesso: bool = False,
    max_colunas: int = 7,
    header_list: list[str] = None,
    placeholder_categoria: str = 'Categoria'
) -> pd.DataFrame:
    """
    Processa uma página de cardápio escolar em formato genérico.

    Parâmetros:
        page: página PDF aberta com pdfplumber.
        num_linhas_cabecalho: número de linhas do cabeçalho da tabela principal.
        col_indices_dias: índices das colunas onde estão os dias da semana no cabeçalho.
        categoria_col_idx: índice da coluna que representa categorias no corpo.
        max_colunas: número máximo de colunas esperadas (para preenchimento).
        aplicar_recesso: se True, aplica RECESSO baseado no texto da página.
        header_list: lista com os nomes dos dias da semana para detectar recessos.
        placeholder_categoria: nome da coluna de categoria no resultado.

    Retorna:
        pd.DataFrame estruturado e agrupado por categoria e dia.
    """
    tables = page.extract_tables()
    text = page.extract_text()

    if not tables or not text:
        return None

    # 🧠 2. Cabeçalho da tabela principal
    header = tables[0][:num_linhas_cabecalho]
    if not col_indices_dias:
        # Assume colunas de dia começando no índice 1 e pulando de 3 em 3
        col_indices_dias = [i for i in range(1, len(header[0]), 3)]

    nomes_dias = []
    for idx in col_indices_dias:
        partes = []
        for row in header:
            if idx < len(row):
                partes.append((row[idx] or "").strip())
        nomes_dias.append(" ".join(partes).strip())

    if len(nomes_dias) < 1:
        return None

    colunas_finais = [placeholder_categoria] + nomes_dias

    # 🧠 3. Corpo da tabela
    body_raw = [row for table in tables[1:] for row in table]
    clean_body = [row for row in body_raw if row and any(cell and cell.strip() for cell in row)]

    def ajustar_linha(row):
        row = row + [None] * (max_colunas - len(row))
        if (not row[5] or row[5].strip() == "") and row[6] and row[6].strip() != "":
            row[5] = row[6]
        return row[:6]

    ajustado = [ajustar_linha(row) for row in clean_body if len(row) >= 2]

    df = pd.DataFrame(ajustado, columns=colunas_finais)
    df[placeholder_categoria] = df[placeholder_categoria].ffill()
    if(transpose):
        # 🧠 4. Transpõe e aplica recessos
        df = df.set_index(placeholder_categoria).T.reset_index()
        df = df.rename(columns={'index': fill})


    # 🧠 5. Agrupamento final por categoria
    agrupadas = defaultdict(list)
    for col in df.columns[1:]:
        agrupadas[col].append(col)

    df_final = pd.DataFrame()
    df_final[fill] = df[fill]

    for categoria, col_list in agrupadas.items():
        if len(col_list) == 1:
            df_final[categoria] = df[col_list[0]]
        else:
            df_final[categoria] = df[col_list].apply(
                lambda row: ' e '.join(dict.fromkeys(filter(None, row))), axis=1
            )

    return df_final
