import pdfplumber

with pdfplumber.open("Cardápio de mes junho - 2025.pdf") as pdf:
    first_page = pdf.pages[0]
    table = first_page.extract_table()
    
    # Para obter como DataFrame do pandas
    import pandas as pd
    df = pd.DataFrame(table[1:], columns=table[0])
    print(df)
