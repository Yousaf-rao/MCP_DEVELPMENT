
from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'LogicPatch Project Analysis', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, label, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        # Latin encoding fix for fpdf: Remove non-latin characters (emojis)
        body = body.encode('latin-1', 'ignore').decode('latin-1')
        self.multi_cell(0, 5, body)
        self.ln()

def create_pdf(md_file, pdf_file):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    with open(md_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_body = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Global sanitation for emojis
        line = line.encode('latin-1', 'ignore').decode('latin-1')
        
        if line.startswith("# "):
            if current_body:
                pdf.chapter_body(current_body)
                current_body = ""
            # Main Title (Skip, handled in header)
            pass
        elif line.startswith("## "):
            if current_body:
                pdf.chapter_body(current_body)
                current_body = ""
            pdf.chapter_title(line.replace("## ", ""))
        elif line.startswith("### "):
            if current_body:
                pdf.chapter_body(current_body)
                current_body = ""
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 6, line.replace("### ", ""), 0, 1)
            pdf.set_font('Arial', '', 11)
        else:
            current_body += line + "\n"
            
    if current_body:
        pdf.chapter_body(current_body)

    pdf.output(pdf_file, 'F')
    print(f"PDF created successfully: {pdf_file}")

if __name__ == "__main__":
    md_path = "LogicPatch_Project_Analysis.md"
    pdf_path = "LogicPatch_Project_Analysis.pdf"
    
    if os.path.exists(md_path):
        create_pdf(md_path, pdf_path)
    else:
        print(f"Error: {md_path} not found.")
