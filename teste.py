import pdfplumber

with pdfplumber.open("cardapio_junho.pdf") as pdf:
    for i, page in enumerate(pdf.pages, start=1):
        text = page.extract_text()
        print(f"--- Página {i} ---\n{text}\n")
