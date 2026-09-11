from markdown_pdf import MarkdownPdf
import markdown_pdf

pdf = MarkdownPdf(toc_level=2)
pdf.add_section(markdown_pdf.Section("README.md"))
pdf.save("TaskFlow_Project_Overview.pdf")
print("PDF Generated successfully: TaskFlow_Project_Overview.pdf")
