import tkinter as tk
from src.gui.gui import ProteinLigandAnalyzerApp
import multiprocessing

def main():
    root = tk.Tk()
    ProteinLigandAnalyzerApp(root)
    root.mainloop()

if __name__ == "__main__":
    multiprocessing.freeze_support()  # Necessary for PyInstaller
    multiprocessing.set_start_method("spawn")  # Ensures proper behavior on Windows
    main()
