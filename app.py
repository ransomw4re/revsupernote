from notebook import Notebook

if __name__ == "__main__":
    filename = "files/1553_sw"

    notebook = Notebook(f"{filename}.note")
    notebook.print_metadata()
