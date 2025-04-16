from notebook import Notebook

if __name__ == "__main__":
    filename = "files/reverse_eng"

    notebook = Notebook(f"{filename}.note")
    notebook.print_metadata()
    notebook.export_pdf()
