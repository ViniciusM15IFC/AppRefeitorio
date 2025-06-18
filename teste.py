import pdfplumber

with pdfplumber.open("cardapio_junho.pdf") as pdf:
    first_page = pdf.pages[0]
    table = first_page.extract_table()
    
    # Para obter como DataFrame do pandas
    import pandas as pd
    df = pd.DataFrame(table[1:], columns=table[0])
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)

    print(df)
    df.to_csv('tabela.csv', index=False)

