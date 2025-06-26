from datetime import datetime
import os
import logging
import threading
import tkinter as tk
import webbrowser
import platform
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkFont
import src.grapher as grapher
from src.data_analysis import analyzer_helper
from src.output.csv_generator import generateCSV
from src.output.pdf_generator import generate_PDF
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.parse import get_number_of_scans, get_max_and_min_mz
from src.catalyst_manager import CATALYST_manager
from src.settings.settings import Settings

class ProteinLigandAnalyzerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("CATALYST")
        self.root.configure(bg="#f5f5f5")# Set background color
        self.error_counter = 0

        # CATALYST dir
        self.catalyst_manager = CATALYST_manager(catalyst_path="PROGRAMDATA", callback_function=self.callback, error_function=self.error)

        # Logging
        logging.basicConfig(
            filename=self.catalyst_manager.LOG_PATH,
            force=True,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Settings
        self.settings = self.catalyst_manager.check()
        self.catalyst_manager.set_cache_threshold(self.settings.advanced_settings.cache_size.value)

        # Mode selection: 0=targeted 1=untargeted
        self.mode = tk.IntVar()
        self.mode.set(0)

        # Timelines and data
        self.scan_date = None
        self.protein = None
        self.ligand = []
        self.ligand_figures = []
        self.figure_counter = 0
        self.root.protocol("WM_DELETE_WINDOW", lambda: confirm_close())

        def confirm_close():
            if messagebox.askyesno("Confirm", "Are you sure you want to close?"):
                self.root.quit()

        # Initialization of GUI elements
        self.next_fig = None
        self.previous_fig = None
        self.exit_button = None
        self.pdf_button = None

        # Default folder where to save the pdf
        if platform.system() == 'Windows':
            try:
                import winreg
                reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
                desktop = winreg.QueryValueEx(reg_key, 'Desktop')[0]
                winreg.CloseKey(reg_key)
            except:
                desktop = "None"
        else:
            desktop = Path.home() / 'Desktop'
            if not os.path.exists(desktop):
                desktop = os.path.normpath(os.path.expanduser("~/Desktop"))
        self.settings.output_settings.output_folder.value = desktop

        # List for tracked ligands
        self.tracked_ligands = []

        # Custom Fonts
        title_font = tkFont.Font(family="Helvetica", size=16, weight="bold")
        self.label_font = tkFont.Font(family="Helvetica", size=12)
        self.section_title_font = tkFont.Font(family="Helvetica", size=10, weight="bold")
        self.button_font = tkFont.Font(family="Helvetica", size=10, weight="bold")

        # Width hardcoded
        self.same_width = 17

        # Title
        title_label = tk.Label(self.root, text="CATALYST", font=title_font, bg="#f5f5f5", fg="#333")
        title_label.pack(pady=(10, 0))

        # Frame for Upload Section
        self.upload_frame = tk.Frame(self.root, bg="#f5f5f5")
        self.upload_frame.pack(pady=2, padx=2)

        # Upload Label and Button
        i = 0
        upload_label = tk.Label(self.upload_frame, text="Upload Mass Spectrometry Data:", font=self.label_font, bg="#f5f5f5", fg="#555")
        upload_label.grid(row=i, column=1, pady=5)
        self.upload_button = tk.Button(self.upload_frame, text="Select File", font=self.button_font, command=self.upload_file, bg="#2196F3", fg="white", height=1, width=self.same_width)
        self.upload_button.grid(row=i, column=2, pady=5)

        # Split radio buttons so that it is fitting to rows into row 0 and 1
        mode1_radio = ttk.Radiobutton(self.upload_frame, text="Targeted", variable=self.mode, value=0, command=lambda: self.show_modi_input(0))
        mode1_radio.grid(row=i, column=5)

        mode2_radio = ttk.Radiobutton(self.upload_frame, text="Untargeted", variable=self.mode, value=1, command=lambda: self.show_modi_input(1))
        mode2_radio.grid(row=i, column=6)
        i += 1

        """
            Protein input section:
            1. Label
            2. Protein m/z: float
            3. Protein charge state: int > 0 
            4. Energy function protein: int
            5. Energy function ligands: int
        """
        protein_input_label = tk.Label(self.upload_frame, text="Protein input:", font=self.section_title_font, bg="#f5f5f5", fg="#555", anchor="w")
        protein_input_label.grid(row=i, column=0, pady=2)
        i += 1

        #Input mass/ charge protein:
        label_mass_over_charge = tk.Label(self.upload_frame, text="Protein m/z:", font=self.label_font, bg="#f5f5f5", fg="#555")
        label_mass_over_charge.grid(row=i, column=0)
        self.entry_mass_over_charge = tk.Entry(self.upload_frame, width=self.same_width, name="mass/charge")
        self.entry_mass_over_charge.grid(row=i, column=1)
        self.entry_mass_over_charge.insert(0, f"{self.settings.general_settings.protein_mz.value or ""}")
        i += 1

        # Input charge protein:
        label_charge = tk.Label(self.upload_frame, text="Protein charge state:", font=self.label_font, bg="#f5f5f5", fg="#555" )
        label_charge.grid(row=i, column=0)
        self.entry_charge = tk.Entry(self.upload_frame, width=self.same_width, name="charge_state")
        self.entry_charge.grid(row=i, column=1)
        self.entry_charge.insert(0, f"{self.settings.general_settings.protein_charge_state.value or ""}")
        i += 1

        label_function_protein = tk.Label(self.upload_frame, text="Energy function protein:", font=self.label_font, bg="#f5f5f5", fg="#555")
        label_function_protein.grid(row=i, column=0)
        self.entry_function_protein = tk.Entry(self.upload_frame, width=self.same_width, name="function_protein")
        self.entry_function_protein.grid(row=i, column=1)
        self.entry_function_protein.insert(0, f"{self.settings.general_settings.function_protein.value}")
        i += 1

        label_function_ligands = tk.Label(self.upload_frame, text="Energy function ligands:", font=self.label_font, bg="#f5f5f5", fg="#555")
        label_function_ligands.grid(row=i, column=0)
        self.entry_function_ligands = tk.Entry(self.upload_frame, width=self.same_width, name="function_ligands")
        self.entry_function_ligands.grid(row=i, column=1)
        self.entry_function_ligands.insert(0, f"{self.settings.general_settings.function_ligand.value}")
        i += 1

        """
            Range inputs section:
            1. Label
            2. Protein sampling range: float
            3. Ligand sampling range: float
        """
        j = 1
        ranges = tk.Label(self.upload_frame, text="Range inputs:", font=self.section_title_font, bg="#f5f5f5", fg="#555")
        ranges.grid(row=j, column=2, pady=2)
        j += 1

        #Radius protein and radius ligand
        label_range_protein = tk.Label(self.upload_frame, text="Protein sampling range:", font=self.label_font, bg="#f5f5f5", fg="#555")
        label_range_protein.grid(row=j, column=2, padx=20)
        self.entry_range_protein = tk.Entry(self.upload_frame, width=self.same_width, name="protein_radius")
        self.entry_range_protein.grid(row=j, column=3)
        self.entry_range_protein.insert(0, f"{self.settings.general_settings.protein_sampling_range.value}")
        j += 1

        label_range_ligand = tk.Label(self.upload_frame, text="Ligand sampling range:", font=self.label_font, bg="#f5f5f5", fg="#555")
        label_range_ligand.grid(row=j, column=2)
        self.entry_range_ligand = tk.Entry(self.upload_frame, width=self.same_width, name="ligand_radius")
        self.entry_range_ligand.grid(row=j, column=3)
        self.entry_range_ligand.insert(0, f"{self.settings.general_settings.ligand_sampling_range.value}")
        j += 1

        """
            Similarity settings section:
            1. Label
            2. DTW threshold: float
            3. Pearson threshold: float (%)
        """
        similarity = tk.Label(self.upload_frame, text="Similarity settings:", font=self.section_title_font, bg="#f5f5f5",fg="#555")
        similarity.grid(row=i, column=0, pady=2)
        i += 1

        label_dtw_threshold = tk.Label(self.upload_frame, text="DTW threshold:", font=self.label_font, bg="#f5f5f5", fg="#555")
        label_dtw_threshold.grid(row=i, column=0)
        self.entry_dtw_threshold = tk.Entry(self.upload_frame, width=self.same_width, name="dtw_threshold")
        self.entry_dtw_threshold.grid(row=i, column=1)
        self.entry_dtw_threshold.insert(0, f"{self.settings.general_settings.dtw_threshold.value}")
        i += 1

        label_pearson_threshold = tk.Label(self.upload_frame, text="Pearson threshold:", font=self.label_font, bg="#f5f5f5", fg="#555")
        label_pearson_threshold.grid(row=i, column=0)
        self.entry_pearson_threshold = tk.Entry(self.upload_frame, width=self.same_width, name="pearson_threshold")
        self.entry_pearson_threshold.grid(row=i, column=1)
        self.entry_pearson_threshold.insert(0, f"{self.settings.general_settings.pearson_threshold.value}")
        i += 1

        """
            Analysis range settings section:
            1. Label
            2. Analysis scan-start: int >= 0 
            3. Analysis scan-end: int > start
        """
        analysis = tk.Label(self.upload_frame, text="Analysis range settings:", font=self.section_title_font, bg="#f5f5f5", fg="#555")
        analysis.grid(row=j, column=2, pady=2)
        j += 1

        label_start_x_analysis= tk.Label(self.upload_frame, text="Analysis scan-start:", font=self.label_font, bg="#f5f5f5", fg="#555")
        label_start_x_analysis.grid(row=j, column=2)
        self.entry_start_x_analysis = tk.Entry(self.upload_frame, width=self.same_width, name="analysis_start")
        self.entry_start_x_analysis.grid(row=j, column=3)
        self.entry_start_x_analysis.insert(0, f"{self.settings.general_settings.analysis_start.value}")
        j += 1

        label_end_x_analysis= tk.Label(self.upload_frame, text="Analysis scan-end:", font=self.label_font, bg="#f5f5f5", fg="#555")
        label_end_x_analysis.grid(row=j, column=2)
        self.entry_end_x_analysis = tk.Entry(self.upload_frame, width=self.same_width, name="analysis_end")
        self.entry_end_x_analysis.grid(row=j, column=3)
        self.entry_end_x_analysis.insert(0, f"{self.settings.general_settings.analysis_end.value}")
        j += 1

        self.output_frame = tk.Frame(self.root, bg="#f5f5f5")
        self.output_frame.pack(pady=0)

        """
            Output settings section:
            1. Label
            2. Result folder
            3. Protein & Ligand graphs in
            4. Create .csv files
        """
        j = 0
        output = tk.Label(self.output_frame, text="Output settings:", font=self.section_title_font, bg="#f5f5f5", fg="#555")
        output.grid(row=j, column=0, pady=2, padx=5)
        j += 1

        result_label = tk.Label(self.output_frame, text="Result folder:", font=self.label_font, bg="#f5f5f5", fg="#555")
        result_label.grid(row=j, column=0)
        self.result_button = tk.Button(self.output_frame, text="Select Folder", command=lambda: self.save_output_folder(), font=self.button_font, bg="#2196F3", fg="white", height=1, width=self.same_width)
        self.result_button.grid(row=j, column=1, padx=5, pady=2)
        j += 1

        normalization_modes = ["No", "Individual", "Together"]
        self.entry_normalization_mode = tk.StringVar(value=self.settings.output_settings.normalization_mode.value)
        normalization_label = tk.Label(self.output_frame, text="Normalization:", font=self.label_font, bg="#f5f5f5", fg="#555")
        normalization_label.grid(row=j, column=0, pady=5)
        normalization_menu = ttk.OptionMenu(self.output_frame, self.entry_normalization_mode, self.entry_normalization_mode.get(), *normalization_modes)

        normalization_menu.grid(row=j, column=1, padx=5)
        normalization_menu.config(width=self.same_width - 3)
        j += 1

        output_graph_choice = ["One plot", "Two different plots"]
        self.output_choice= tk.StringVar(value=self.settings.output_settings.graph_combination.value)
        output_graph_label= tk.Label(self.output_frame, text="Protein & Ligand graphs in:", font=self.label_font, bg="#f5f5f5", fg="#555")
        output_graph_label.grid(row=j, column=0, padx=5)
        output_graph_menu= ttk.OptionMenu(self.output_frame, self.output_choice, self.output_choice.get(), *output_graph_choice)
        output_graph_menu.grid(row=j, column=1, padx=5)
        output_graph_menu.config(width=self.same_width - 3)
        j += 1


        csv_choice = ["YES", "NO"]
        self.csv_choice = tk.StringVar(value=csv_choice[-int(self.settings.output_settings.csv_files.value) - 1])
        csv_label = tk.Label(self.output_frame, text="Create .csv files:", font=self.label_font, bg="#f5f5f5", fg="#555")
        csv_label.grid(row=j, column=0, padx=5)
        csv_menu = ttk.OptionMenu(self.output_frame, self.csv_choice, self.csv_choice.get(),*csv_choice)
        csv_menu.grid(row=j, column=1, padx=5)
        csv_menu.config(width= self.same_width - 3)
        j += 1

        #import/ export setting
        j=1
        import_settings_label = tk.Label(self.output_frame, text="Import Settings:", font=self.label_font, bg="#f5f5f5", fg="#555")
        import_settings_label.grid(row=j, column=2, padx=5)
        self.import_settings_button = tk.Button(self.output_frame, text="Select File", command=lambda: self.impo_expo_file("import settings"), font=self.button_font, bg="#2196F3", fg="white", height=1, width=self.same_width)
        self.import_settings_button.grid(row=j, column=3, padx=5)
        j += 1

        export_settings_label = tk.Label(self.output_frame, text="Export Settings:", font=self.label_font, bg="#f5f5f5", fg="#555")
        export_settings_label.grid(row=j, column=2, padx=5)
        self.export_settings_button = tk.Button(self.output_frame, text="Select Folder", command=lambda: self.impo_expo_file("export settings"), font=self.button_font, bg="#2196F3", fg="white", height=1, width=self.same_width)
        self.export_settings_button.grid(row=j, column=3, padx=5)
        j += 1


        #Modi Frame with default Targeted Mode
        self.modi_frame = tk.Frame(self.upload_frame, bg="#f5f5f5")
        self.modi_frame.grid(row=1, rowspan=2, column=5, columnspan=2, pady=2, padx=25)
        j = 0

        targeted = tk.Label(self.modi_frame, text="Targeted settings:", font=self.section_title_font, bg="#f5f5f5",fg="#555")
        targeted.grid(row=j, column=0, pady=2, padx=5)
        j += 1

        upload_label = tk.Label(self.modi_frame, text="Select ligands:", font=self.label_font, bg="#f5f5f5", fg="#555")
        upload_label.grid(row=j, column=0, padx=20)
        self.ligands_upload_button = tk.Button(self.modi_frame, text="Select File", font=self.button_font, command=self.read_ligands, bg="#2196F3", fg="white", height=1, width=self.same_width)
        self.ligands_upload_button.grid(row=j, column=1, padx=5)

        self.analyze_frame= tk.Frame(self.root, bg="#f5f5f5")
        self.analyze_frame.pack(fill="x")

        # File Path Display
        self.file_label = tk.Label(self.analyze_frame, text="", font=self.label_font, fg="#0066cc", bg="#f5f5f5")

        self.output_folder_label = tk.Label(self.analyze_frame, text="", font=self.label_font, fg="#0066cc", bg="#f5f5f5")

        self.ligand_label = tk.Label(self.analyze_frame, text="", font=self.label_font, fg="#0066cc", bg="#f5f5f5")

        self.output_folder_label = tk.Label(self.analyze_frame, text="", font=self.label_font, fg="#0066cc", bg="#f5f5f5")

        self.cache_import_label = tk.Label(self.analyze_frame, text="", font=self.label_font, fg="#0066cc", bg="#f5f5f5")

        self.cache_export_label = tk.Label(self.analyze_frame, text="", font=self.label_font, fg="#0066cc", bg="#f5f5f5")

        self.import_settings_label = tk.Label(self.analyze_frame, text="", font=self.label_font, fg="#0066cc", bg="#f5f5f5")

        self.export_settings_label = tk.Label(self.analyze_frame, text="", font=self.label_font, fg="#0066cc", bg="#f5f5f5")

        give_me_space4 = tk.Label(self.analyze_frame, text="  ", bg="#f5f5f5")
        give_me_space4.pack()

        # Advanced Settings Button
        self.adv_settings_button = tk.Button(self.analyze_frame, text="Advanced Settings", font=self.button_font, command=lambda: self.change_adv_settings(), bg="#2196F3", fg="white", width=self.same_width)
        self.adv_settings_button.pack()

        # Analyze Button
        self.analyze_button = tk.Button(self.analyze_frame, text="Analyze Data", font=self.button_font, command=self.analyze_data, state=tk.DISABLED, bg="#2196F3", fg="white", width=self.same_width)
        self.analyze_button.pack()

        self.help_button = tk.Button(self.analyze_frame, text="Help", font=self.button_font, command=lambda: self.open_help_pdf(), bg="red", fg="white", width=self.same_width)
        self.help_button.pack()

        give_me_space5 = tk.Label(self.analyze_frame, text="  ", bg="#f5f5f5")
        give_me_space5.pack()

        # Results Display Area
        self.result_frame = tk.Frame(self.root, bg="#f5f5f5")
        self.result_frame.pack(pady=2, padx=5, fill="x")

        self.result_text = tk.Text(self.result_frame, height=10, width=60, font=("Courier", 10), bg="#f9f9f9", fg="#333", state= "disabled")
        self.result_text.pack(side="left", fill="both", expand=True)

        # Scrollbar for Result Text
        scrollbar = tk.Scrollbar(self.result_frame, command=self.result_text.yview)
        scrollbar.pack(pady=(10, 20), side="right")
        self.result_text.config(yscrollcommand=scrollbar.set)


        #Graphs display area
        self.graph_frame= tk.Frame(self.root, bg="#f5f5f5")
        self.graph_frame.pack(pady=(10, 20), padx=10, fill="x")

    def show_modi_input(self, modus):
        self.mode.set(modus)
        i = 1
        for widget in self.modi_frame.winfo_children():
            widget.destroy()
        #targeted
        if modus == 0:
            self.modi_frame.grid_configure(rowspan= 2)
            targeted = tk.Label(self.modi_frame, text="Targeted settings:", font=self.section_title_font, bg="#f5f5f5", fg="#555")
            targeted.grid(row=i, column=5, pady=2, padx=20)
            i += 1

            ligands_upload_label = tk.Label(self.modi_frame, text="Select ligands:", font=self.label_font, bg="#f5f5f5", fg="#555")
            ligands_upload_label.grid(row=i, column=5)
            self.ligands_upload_button = tk.Button(self.modi_frame, text="Select File", font=self.button_font, command= self.read_ligands, bg="#2196F3", fg="white", height=1, width=self.same_width)
            self.ligands_upload_button.grid(row=i, column=6)

        elif modus == 1:
            """
                Untracked Settings Section:
                1. Label
                2. Protein charge state exclusion range: int
                3. Start m/z: float
                4. End m/z: float
                5. Ligand m/z grouping range: int
                6. Protein exclusion window: int
            """
            self.modi_frame.grid_configure(rowspan=6)
            untargeted = tk.Label(self.modi_frame, text="Untargeted settings:", font=self.section_title_font, bg="#f5f5f5", fg="#555")
            untargeted.grid(row=i, column=5)

            i += 1

            label_charge_exclusion_range = tk.Label(self.modi_frame, text="Protein charge state exclusion range:", font=self.label_font, bg="#f5f5f5", fg="#555")
            label_charge_exclusion_range.grid(row=i, column=5, padx=20)
            self.entry_charge_exclusion_range = tk.Entry(self.modi_frame, width=self.same_width, name="charge_state_exclusion")
            self.entry_charge_exclusion_range.grid(row=i, column=6)
            self.entry_charge_exclusion_range.insert(0, f"{self.settings.untargeted_settings.charge_state_exclusion.value}")
            i += 1

            label_start_value_mz = tk.Label(self.modi_frame, text="Start m/z:", font=self.label_font, bg="#f5f5f5", fg="#555")
            label_start_value_mz.grid(row=i, column=5)
            self.entry_start_value_mz = tk.Entry(self.modi_frame, width=self.same_width, name="start_mz")
            self.entry_start_value_mz.grid(row=i, column=6)
            self.entry_start_value_mz.insert(0, f"{self.settings.untargeted_settings.start_mz.value}")
            i += 1

            label_end_value_mz = tk.Label(self.modi_frame, text="End m/z:", font=self.label_font, bg="#f5f5f5", fg="#555")
            label_end_value_mz.grid(row=i, column=5)
            self.entry_end_value_mz = tk.Entry(self.modi_frame, width=self.same_width, name="end_mz")
            self.entry_end_value_mz.grid(row=i, column=6)
            self.entry_end_value_mz.insert(0, f"{self.settings.untargeted_settings.end_mz.value}")
            i += 1

            label_range_threshold_ligand = tk.Label(self.modi_frame, text="Ligand m/z grouping range:", font=self.label_font, bg="#f5f5f5", fg="#555")
            label_range_threshold_ligand.grid(row=i, column=5)
            self.entry_range_threshold_ligand = tk.Entry(self.modi_frame, width=self.same_width, name="ligand_group_range")
            self.entry_range_threshold_ligand.grid(row=i, column=6)
            self.entry_range_threshold_ligand.insert(0, f"{self.settings.untargeted_settings.ligand_group_range.value}")
            i += 1

            label_protein_exclusion_window = tk.Label(self.modi_frame, text="Protein exclusion window:", font=self.label_font,bg="#f5f5f5", fg="#555")
            label_protein_exclusion_window.grid(row=i, column=5)
            self.entry_protein_exclusion_window = tk.Entry(self.modi_frame, width=self.same_width, name="protein_exclusion_window")
            self.entry_protein_exclusion_window.grid(row=i, column=6)
            self.entry_protein_exclusion_window.insert(0, f"{self.settings.untargeted_settings.protein_exclusion_window.value}")

    #explanation for disabled x-closed button in advanced setting
    def x_closing_adv_setting(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to quit without saving?"):
            self.adv_settings.destroy()
        else:
            self.adv_settings.focus_force()

    def change_adv_settings(self):
        """
            Opens a new window to change the advanced settings.
        """
        self.adv_settings = tk.Toplevel(self.root)

        self.adv_settings.title("Advanced Settings")
        self.adv_settings.configure(bg="#f5f5f5")
        same_width=12
        label_font = tkFont.Font(family="Helvetica", size=12)

        #Deactivates "x"-closing button
        self.adv_settings.protocol("WM_DELETE_WINDOW", lambda: self.x_closing_adv_setting())

        """
            1. Empty
            2. Protein charge state sum range: int
            3. Savitzky-Golay filter window length: int
            4. Savitzky-Golay filter polyorder: int
            5. Normalization Mode: int
            6. Num of parse processes: int
            7. Num of analysis processes: int
            8. Max cache size (GB): float
            9. Use Cache: bool
        """
        i = 0
        give_me_space= tk.Label(self.adv_settings, text="  ", bg="#f5f5f5")
        give_me_space.grid(row=i, column=1)
        i+=1

        label_avg_charge_range = tk.Label(self.adv_settings, text="Protein charge state sum range:", font=label_font, bg="#f5f5f5", fg="#555")
        label_avg_charge_range.grid(row=i, column=0)
        self.entry_avg_charge_range = tk.Entry(self.adv_settings, width=same_width, name="charge_state_sum")
        self.entry_avg_charge_range.grid(row=i, column=1)
        i += 1

        label_filter_window_length = tk.Label(self.adv_settings, text="Savitzky-Golay filter window length:", font=label_font, bg="#f5f5f5", fg="#555")
        label_filter_window_length.grid(row=i, column=0)
        self.entry_filter_window_length = tk.Entry(self.adv_settings, width=same_width, name="filter_window")
        self.entry_filter_window_length.grid(row=i, column=1)
        i += 1

        label_filter_polyorder = tk.Label(self.adv_settings, text="Savitzky-Golay filter polyorder:", font=label_font, bg="#f5f5f5", fg="#555")
        label_filter_polyorder.grid(row=i, column=0)
        self.entry_filter_polyorder = tk.Entry(self.adv_settings, width=same_width, name="filter_polyorder")
        self.entry_filter_polyorder.grid(row=i, column=1)
        i += 1

        label_num_process = tk.Label(self.adv_settings, text="Num of parse processes:", font=label_font, bg="#f5f5f5", fg="#555")
        label_num_process .grid(row=i, column=0)
        self.entry_num_process = tk.Entry(self.adv_settings, width=same_width, name="parse_processes")
        self.entry_num_process.grid(row=i, column=1)
        i += 1

        label_num_process_analysis = tk.Label(self.adv_settings, text="Num of analysis processes:", font=label_font, bg="#f5f5f5", fg="#555")
        label_num_process_analysis.grid(row=i, column=0)
        self.entry_num_process_analysis = tk.Entry(self.adv_settings, width=same_width, name="analysis_processes")
        self.entry_num_process_analysis.grid(row=i, column=1)
        i += 1

        label_max_cache_size = tk.Label(self.adv_settings, text="Max cache size (GB):", font=label_font, bg="#f5f5f5", fg="#555")
        label_max_cache_size.grid(row=i, column=0)
        self.entry_max_cache_size = tk.Entry(self.adv_settings, width=same_width, name="cache_size")
        self.entry_max_cache_size.grid(row=i, column=1)
        i += 1

        cache_choice = ["YES", "NO"]
        self.entry_cache_use = tk.StringVar(value=cache_choice[-int(self.settings.advanced_settings.use_cache.value) - 1])
        label_cache_use = tk.Label(self.adv_settings, text="Use Cache:", font=label_font, bg="#f5f5f5", fg="#555")
        label_cache_use.grid(row=i, column=0, pady=2)
        cache_menu = ttk.OptionMenu(self.adv_settings, self.entry_cache_use, self.entry_cache_use.get(), *cache_choice)

        cache_menu.grid(row=i, column=1, pady=2, padx=5)
        cache_menu.config(width=self.same_width - 8)
        i += 1

        give_me_space3 = tk.Label(self.adv_settings, text="  ", bg="#f5f5f5")
        give_me_space3.grid(row=i, column=1)
        i += 1

        cache_imp_expo_frame= tk.Frame(self.adv_settings)
        cache_imp_expo_frame.grid(row=i, column=0, rowspan=3)
        j = i

        self.import_cache = tk.Button(cache_imp_expo_frame, text="Import cache", font=label_font, command=lambda: self.impo_expo_file("import cache"), bg="#2196F3", fg="white", width=same_width)
        self.import_cache.grid(row=j, column=0)
        j += 1

        self.export_cache = tk.Button(cache_imp_expo_frame, text="Export cache", font=label_font, command=lambda: self.impo_expo_file("export cache"), bg="#2196F3", fg="white", width=same_width)
        self.export_cache.grid(row=j, column=0)
        j += 1

        del_cache = tk.Button(cache_imp_expo_frame, text="Empty cache", font=label_font, command=lambda: self.cache_clear(), bg="#2196F3", fg="white", width=same_width)
        del_cache.grid(row=j, column=0)

        #self.adv_error_text = tk.Text(self.adv_settings, height=10, width=60, font=("Courier", 10), bg="#f9f9f9", fg="#333", state="disabled")

        save_and_close_button = tk.Button(self.adv_settings, text="Save&close", font=label_font, command=lambda: self.save_adv_settings(), bg="#2196F3", fg="white", width=same_width)
        save_and_close_button.grid(row=i, column=1, padx=10)
        i += 1

        reset_button = tk.Button(self.adv_settings, text="Reset", font=label_font, command=lambda: self.fill_values_adv_settings(True) , bg="#2196F3",fg="white", width=same_width)
        reset_button.grid(row=i, column=1, padx=10)
        i += 1

        help_button = tk.Button(self.adv_settings, text="Help", font=label_font, command=lambda: self.open_help_pdf(), bg="red", fg="white", width=same_width)
        help_button.grid(row=i, column=1, padx=10)
        i+=1

        give_me_space2 = tk.Label(self.adv_settings, text="  ", bg="#f5f5f5")
        give_me_space2.grid(row=i, column=1)

        self.fill_values_adv_settings(False)

    def save_adv_settings(self):
        try:
            self.settings.advanced_settings.charge_state_sum.value = self.type_returning_int(self.entry_avg_charge_range,"Advanced settings: Protein charge state sum range")
            self.settings.advanced_settings.filter_window.value = self.type_returning_int(self.entry_filter_window_length, "Advanced settings: Savitzky-Golay filter window length")
            self.settings.advanced_settings.filter_polyorder.value = self.type_returning_int(self.entry_filter_polyorder, "Advanced settings: Savitzky-Golay filter polyorder")
            self.settings.advanced_settings.parse_processes.value = self.type_returning_int(self.entry_num_process, "Advanced settings: Num of parse processes")
            self.settings.advanced_settings.analysis_processes.value = self.type_returning_int(self.entry_num_process_analysis, "Advanced settings: Num of analysis processes")
            self.settings.advanced_settings.cache_size.value = self.type_returning_float(self.entry_max_cache_size, "Advanced settings: Max cache size (GB)")
            self.catalyst_manager.set_cache_threshold(self.settings.advanced_settings.cache_size.value)
            self.settings.advanced_settings.use_cache.value = self.entry_cache_use.get() == "YES"
            self.adv_settings.destroy()
        except ValueError as e:
            self.error(str(e), "log show")
            self.adv_settings.focus_force()


    @staticmethod
    def del_refill_entry(entry, entry_input):
        entry.delete(0, tk.END)
        entry.insert(0, f"{entry_input}")


    def callback(self, message: str, mtype: str, tag=None):
        if "log" in mtype:
            logging.info(message)
        if "print" in mtype:
            self.update_result_text(message,tag)

    def error(self, message: str, mtype: str, tag=None):
        if "log" in mtype:
            logging.error(message)
        if "print" in mtype:
            self.update_result_text(f"ERROR: {message}", tag)
        if "show" in mtype:
            self.show_error(message)


    def update_result_text(self, message, tag=None):
        if not hasattr(self, "result_text"):
            return
        def insert_text():
            self.result_text.config(state="normal")
            self.result_text.insert(tk.END, f"{message}\n", tag if tag else "")
            self.result_text.config(state="disabled")
            self.result_text.see(tk.END)  # Scroll to the bottom
        self.result_text.after(0, insert_text)


    def fill_values_adv_settings(self, default):
        if default:
            if messagebox.askokcancel("Confirm", "Are you sure you want to reset the advanced settings?"):
                self.settings.advanced_settings = Settings().advanced_settings
                self.adv_settings.focus_force()
            else:
                self.adv_settings.focus_force()
                return

        self.del_refill_entry(self.entry_avg_charge_range, self.settings.advanced_settings.charge_state_sum.value)
        self.del_refill_entry(self.entry_filter_window_length, self.settings.advanced_settings.filter_window.value)
        self.del_refill_entry(self.entry_filter_polyorder, self.settings.advanced_settings.filter_polyorder.value)
        self.del_refill_entry(self.entry_num_process, self.settings.advanced_settings.parse_processes.value)
        self.del_refill_entry(self.entry_num_process_analysis, self.settings.advanced_settings.analysis_processes.value)
        self.del_refill_entry(self.entry_max_cache_size, self.settings.advanced_settings.cache_size.value)
        self.catalyst_manager.set_cache_threshold(self.settings.advanced_settings.cache_size.value)
        self.entry_cache_use.set("YES" if self.settings.advanced_settings.use_cache.value else "NO")

    @staticmethod
    def type_returning_float(entry, name):
        try:
            entry = float(entry.get())
            return entry
        except ValueError:
            raise ValueError(f"{name} needs to be a Float!")

    @staticmethod
    def type_returning_int(entry, name):
        try:
            entry = int(entry.get())
            return entry
        except ValueError:
            raise ValueError(f"{name} needs to be an Integer!")

    def upload_file(self, file_path: str = "None", loading_setting: bool =  False):
        # Open file dialog to select mass spectrometry data file
        if file_path == "None":
            file_path = filedialog.askopenfilename(title="Select your data file" ,filetypes=[("Mass spectrometric Data", ["*.ms1", "*.txt"])])
        elif file_path and not os.path.exists(file_path):
            file_path = None
            self.settings.general_settings.data_path.value = None

        if file_path:
            self.settings.general_settings.data_path.value = file_path
            self.upload_button.config(bg="green")
            self.file_label.config(text=f"Input data file: {self.settings.general_settings.data_path.value}")
            self.file_label.pack()
            self.analyze_button.config(state=tk.NORMAL)  # Enable the Analyze button

            try:
                # Fill in the last scan number
                if not loading_setting:
                    self.settings.general_settings.analysis_end.value = get_number_of_scans(file_path, self.callback)
                    self.entry_end_x_analysis.delete(0, tk.END)
                    self.entry_end_x_analysis.insert(0, f"{self.settings.general_settings.analysis_end.value}")

                    # Get min/max m/z values from file
                    max_mz, min_mz = get_max_and_min_mz(file_path, self.callback)
                    self.settings.untargeted_settings.start_mz.value = float(int(min_mz))
                    self.settings.untargeted_settings.end_mz.value = float(int(max_mz + 0.9999))
            except ValueError as e:
                self.error(str(e), "log print")
            except FileNotFoundError as e:
                self.error(str(e), "log show")

            if self.mode.get() == 1 and not loading_setting:
                self.entry_start_value_mz.delete(0, tk.END)
                self.entry_start_value_mz.insert(0, f"{self.settings.untargeted_settings.start_mz.value}")
                self.entry_end_value_mz.delete(0, tk.END)
                self.entry_end_value_mz.insert(0, f"{self.settings.untargeted_settings.end_mz.value}")
        else:
            self.upload_button.config(bg="#2196F3")
            self.file_label.forget()

    def read_ligands(self, file_path:str = "None"):
        if file_path == "None":
            file_path = filedialog.askopenfilename(title="Select ligand file", filetypes=[("Ligand input data", ["*.txt"])])
        elif file_path and not os.path.exists(file_path):
            file_path = None
            self.settings.targeted_settings.ligands_path.value = None

        if file_path:
            self.tracked_ligands = []
            with open(file_path, 'r') as file:
                for line in file:
                    try:
                        self.tracked_ligands.append(float(line.strip()))
                    except ValueError:
                        self.error("Not all ligand masses in the given file are convertable to float.", "log print")
                        self.tracked_ligands = []
                        break

            self.settings.targeted_settings.ligands_path.value = file_path
            self.ligands_upload_button.config(bg="green")
            self.ligand_label.config(text=f"Ligand file: {self.settings.targeted_settings.ligands_path.value}")
            self.ligand_label.pack()

            self.callback(f"Read ligands: {self.tracked_ligands}", "log")
            self.settings.targeted_settings.ligands_path.value = file_path
        else:
            self.ligands_upload_button.config(bg="#2196F3")
            self.ligands_upload_button.forget()

    def save_output_folder(self, folder_path: str = "None"):
        if folder_path == "None":
            folder_path = filedialog.askdirectory(title="Select a folder in which the results folder will be saved")
        elif folder_path and not os.path.exists(folder_path):
            folder_path = None
            self.settings.output_settings.output_folder.value = None

        if folder_path:
            self.settings.output_settings.output_folder.value = folder_path
            self.result_button.config(bg="green")
            self.output_folder_label.config(text=f"Output folder: {self.settings.output_settings.output_folder.value}")
            self.output_folder_label.pack()
        else:
            self.result_button.config(bg="#2196F3")
            self.output_folder_label.forget()

    def impo_expo_file(self, mode):
        #cache import
        if mode == "import cache":
            impo_cache_path = filedialog.askopenfilename(title="Select a cache zip-folder" ,filetypes=[("Cache import", ["*.zip"])])
            if impo_cache_path:
                try:
                    self.catalyst_manager.import_cache(impo_cache_path)
                except Exception as e:
                    self.import_cache.config(bg="#2196F3")
                    self.import_settings_label.forget()
                    self.error(str(e), "log show")
                    self.adv_settings.focus_force()
                    return

                self.import_cache.config(bg="green")
                self.cache_import_label.config(text=f"Import cache zip file: {impo_cache_path}")
                self.cache_import_label.pack()
            else:
                self.import_cache.config(bg="#2196F3")
                self.import_settings_label.forget()

            self.adv_settings.focus_force()
            return

        #cache export
        elif mode == "export cache":
            expo_cache_path = filedialog.askdirectory(title="Select a folder where the cache is export to as a zip-folder")
            if expo_cache_path:
                try:
                    self.catalyst_manager.export_cache(expo_cache_path)
                except Exception as e:
                    self.export_cache.config(bg="#2196F3")
                    self.cache_export_label.forget()
                    self.error(str(e), "log show")
                    self.adv_settings.focus_force()
                    return

                self.export_cache.config(bg="green")
                self.cache_export_label.config(text=f"Export cache folder: {expo_cache_path}")
                self.cache_export_label.pack()
            else:
                self.export_cache.config(bg="#2196F3")
                self.cache_export_label.forget()

            self.adv_settings.focus_force()
            return

        #settings import
        elif mode == "import settings":
            import_path = filedialog.askopenfilename(title="Select a CATALYST settings file",filetypes=[("Import settings", ["*.txt"])])
            if import_path:
                try:
                    self.settings = self.catalyst_manager.import_settings(import_path)
                except Exception as e:
                    self.import_settings_button.config(bg="#2196F3")
                    self.import_settings_label.forget()
                    self.error(str(e), "log show")
                    return

                self.update_settings()

                self.import_settings_button.config(bg="green")
                self.import_settings_label.config(text=f"Import settings file: {import_path}")
                self.import_settings_label.pack()
            else:
                self.import_settings_button.config(bg="#2196F3")
                self.import_settings_label.forget()

        #settingsexport
        elif mode == "export settings":
            export_path= filedialog.askdirectory(title="Select a folder where the CATALYST settings file is export to")
            if export_path:
                try:
                    self.store_fields_in_settings()

                    self.catalyst_manager.export_settings(self.settings, export_path)
                except Exception as e:
                    self.export_settings_button.config(bg="#2196F3")
                    self.export_settings_label.forget()
                    self.error(str(e), "log show")
                    return

                self.export_settings_button.config(bg="green")
                self.export_settings_label.config(text=f"Export settings folder: {export_path}")
                self.export_settings_label.pack()
            else:
                self.export_settings_button.config(bg="#2196F3")
                self.export_settings_label.forget()

    def store_fields_in_settings(self):
        self.settings.general_settings.protein_mz.value = self.type_returning_float(self.entry_mass_over_charge, "Protein m/z")
        self.settings.general_settings.protein_charge_state.value = self.type_returning_int(self.entry_charge, "Protein charge state")
        self.settings.general_settings.function_protein.value = self.type_returning_int(self.entry_function_protein, "Energy function protein")
        self.settings.general_settings.function_ligand.value = self.type_returning_int(self.entry_function_ligands, "Energy function ligands")

        self.settings.general_settings.protein_sampling_range.value = self.type_returning_float(self.entry_range_protein, "Protein sampling range")
        self.settings.general_settings.ligand_sampling_range.value = self.type_returning_float(self.entry_range_ligand, "Ligand sampling range")

        self.settings.general_settings.dtw_threshold.value = self.type_returning_float(self.entry_dtw_threshold, "DTW threshold")
        self.settings.general_settings.pearson_threshold.value = self.type_returning_float(self.entry_pearson_threshold, "Pearson threshold")

        self.settings.general_settings.analysis_start.value = self.type_returning_int(self.entry_start_x_analysis, "Analysis scan-start")
        self.settings.general_settings.analysis_end.value = self.type_returning_int(self.entry_end_x_analysis, "Analysis scan-end")

        self.settings.general_settings.analysis_mode.value = {0: "Targeted", 1: "Untargeted"}[self.mode.get()]

        if self.mode.get() == 1:
            self.settings.untargeted_settings.charge_state_exclusion.value = self.type_returning_int(self.entry_charge_exclusion_range, "Protein charge state exclusion range")
            self.settings.untargeted_settings.start_mz.value = self.type_returning_float(self.entry_start_value_mz, "Start m/z")
            self.settings.untargeted_settings.end_mz.value = self.type_returning_float(self.entry_end_value_mz, "End m/z")
            self.settings.untargeted_settings.ligand_group_range.value = self.type_returning_float(self.entry_range_threshold_ligand, "Ligand m/z grouping range")
            self.settings.untargeted_settings.protein_exclusion_window.value = self.type_returning_float(self.entry_protein_exclusion_window, "Protein exclusion window")

        self.settings.output_settings.graph_combination.value = self.output_choice.get()
        self.settings.output_settings.normalization_mode.value = self.entry_normalization_mode.get()
        self.settings.output_settings.csv_files.value = self.csv_choice.get() == "YES"

    def update_settings(self):
        self.upload_file(self.settings.general_settings.data_path.value, True)
        self.update_setting(self.entry_mass_over_charge, f"{self.settings.general_settings.protein_mz.value or ""}")
        self.update_setting(self.entry_charge, f"{self.settings.general_settings.protein_charge_state.value or ""}")
        self.update_setting(self.entry_function_protein, f"{self.settings.general_settings.function_protein.value}")
        self.update_setting(self.entry_function_ligands, f"{self.settings.general_settings.function_ligand.value}")
        self.update_setting(self.entry_range_protein, f"{self.settings.general_settings.protein_sampling_range.value}")
        self.update_setting(self.entry_range_ligand, f"{self.settings.general_settings.ligand_sampling_range.value}")
        self.update_setting(self.entry_dtw_threshold, f"{self.settings.general_settings.dtw_threshold.value}")
        self.update_setting(self.entry_pearson_threshold, f"{self.settings.general_settings.pearson_threshold.value}")
        self.update_setting(self.entry_start_x_analysis, f"{self.settings.general_settings.analysis_start.value}")
        self.update_setting(self.entry_end_x_analysis, f"{self.settings.general_settings.analysis_end.value}")

        if self.settings.general_settings.analysis_mode.value == "Targeted":
            self.show_modi_input(0)
            self.read_ligands(self.settings.targeted_settings.ligands_path.value)

        if self.settings.general_settings.analysis_mode.value == "Untargeted":
            self.show_modi_input(1)
            self.update_setting(self.entry_charge_exclusion_range, f"{self.settings.untargeted_settings.charge_state_exclusion.value}")
            self.update_setting(self.entry_start_value_mz, f"{self.settings.untargeted_settings.start_mz.value}")
            self.update_setting(self.entry_end_value_mz, f"{self.settings.untargeted_settings.end_mz.value}")
            self.update_setting(self.entry_range_threshold_ligand, f"{self.settings.untargeted_settings.ligand_group_range.value}")
            self.update_setting(self.entry_protein_exclusion_window, f"{self.settings.untargeted_settings.protein_exclusion_window.value}")

        self.save_output_folder(self.settings.output_settings.output_folder.value)
        self.entry_normalization_mode.set(self.settings.output_settings.normalization_mode.value)
        self.output_choice.set(self.settings.output_settings.graph_combination.value)
        self.csv_choice.set("YES" if self.settings.output_settings.csv_files.value else "NO")

        # Advanced settings are read from self.settings when window is opened

    @staticmethod
    def update_setting(entry: tk.Entry, value: str):
        entry.delete(0, tk.END)
        entry.insert(0, value)

    def cache_clear(self):
        if messagebox.askokcancel("Confirm", "Are you sure you want to clear your cache?"):
            self.catalyst_manager.fully_clear_cache()

        self.adv_settings.focus_force()

    @staticmethod
    def open_help_pdf():
        webbrowser.open_new_tab('http://github.com/BP-Gruppe-10/MSDA/blob/main/Guide.pdf')

    @staticmethod
    def delete_textinput(textbox):
        textbox.config(state=tk.NORMAL)
        textbox.delete("1.0", tk.END)
        textbox.config(state= tk.DISABLED)

    # Clears the gui and reads the input mass
    # Gives the analyzer the file and gets from it the protein and ligand numbers
    # Generates the figures and a pdf -> using grapher
    def analyze_data(self):
        self.analyze_button.config(state=tk.DISABLED)  # Disable the Analyze button
        self.delete_textinput(self.result_text)
        self.result_text.update()

        try:
            self.store_fields_in_settings()
            if self.mode.get() == 0:
                if not self.tracked_ligands:
                    raise ValueError("No ligands selected!")

        except ValueError as e:
            self.error(str(e), "log show")
            self.analyze_button.config(state=tk.NORMAL)
            return

        self.settings.output_settings.graph_combination.value = self.output_choice.get()
        self.settings.output_settings.csv_files.value = self.output_choice.get() == "YES"

        if self.result_text.get("1.0", "end").strip() == "":
            # Start the background thread for the analysis
            if self.mode.get() == 1:
                analysis_thread = threading.Thread(target=self.run_untargeted_analysis)
                analysis_thread.start()
            else:
                analysis_thread = threading.Thread(target=self.run_targeted_analysis)
                analysis_thread.start()

        else:
            self.analyze_button.config(state=tk.NORMAL)

    def run_untargeted_analysis(self):

        try:
            self.ligand = []
            filtered_mz_values, self.ligand, unnormalized_ligand_curves, filtered_results, self.protein, self.scan_date = analyzer_helper.analyze_untargeted(
                file_path=self.settings.general_settings.data_path.value,
                protein_mz_value=self.settings.general_settings.protein_mz.value,
                protein_charge_state=self.settings.general_settings.protein_charge_state.value,
                function_protein=self.settings.general_settings.function_protein.value,
                function_ligand=self.settings.general_settings.function_ligand.value,
                range_protein=self.settings.general_settings.protein_sampling_range.value,
                range_ligand=self.settings.general_settings.ligand_sampling_range.value,
                dtw_threshold=self.settings.general_settings.dtw_threshold.value,
                pearson_threshold=self.settings.general_settings.pearson_threshold.value,
                start_x_axis=self.settings.general_settings.analysis_start.value,
                end_x_axis=self.settings.general_settings.analysis_end.value,
                charge_state_radius=self.settings.untargeted_settings.charge_state_exclusion.value,
                start_value=self.settings.untargeted_settings.start_mz.value,
                end_value=self.settings.untargeted_settings.end_mz.value,
                range_threshold=self.settings.untargeted_settings.ligand_group_range.value,
                protein_range_threshold=self.settings.untargeted_settings.protein_exclusion_window.value,
                protein_charge_state_averaging_window=self.settings.advanced_settings.charge_state_sum.value,
                window_length=self.settings.advanced_settings.filter_window.value,
                polyorder=self.settings.advanced_settings.filter_polyorder.value,
                normalization_mode={"No": 1, "Individual": 2, "Together": 3}[self.settings.output_settings.normalization_mode.value],
                num_processes=self.settings.advanced_settings.parse_processes.value,
                num_processes_analysis=self.settings.advanced_settings.analysis_processes.value,
                use_cache= self.settings.advanced_settings.use_cache.value,
                catalyst_manager=self.catalyst_manager,
                callback_function=self.callback,
                error_function=self.error
            )

            # Once the analysis is complete, update the GUI
            self.update_gui_after_analysis(filtered_mz_values, filtered_results, unnormalized_ligand_curves)
        except Exception as e:
            self.error(f"Error during analysis: {str(e)}", "log show")


    def run_targeted_analysis(self):
        try:
            # Perform the analysis
            self.ligand = []
            filtered_mz_values, self.ligand, unnormalized_ligand_curves, filtered_results, self.protein, self.scan_date = analyzer_helper.analyze_targeted(
                file_path=self.settings.general_settings.data_path.value,
                protein_mz_value=self.settings.general_settings.protein_mz.value,
                protein_charge_state=self.settings.general_settings.protein_charge_state.value,
                function_protein=self.settings.general_settings.function_protein.value,
                function_ligand=self.settings.general_settings.function_ligand.value,
                range_protein=self.settings.general_settings.protein_sampling_range.value,
                range_ligand=self.settings.general_settings.ligand_sampling_range.value,
                dtw_threshold=self.settings.general_settings.dtw_threshold.value,
                pearson_threshold=self.settings.general_settings.pearson_threshold.value,
                start_x_axis=self.settings.general_settings.analysis_start.value,
                end_x_axis=self.settings.general_settings.analysis_end.value,
                ligand_mz_values= self.tracked_ligands,
                protein_charge_state_averaging_window=self.settings.advanced_settings.charge_state_sum.value,
                window_length=self.settings.advanced_settings.filter_window.value,
                polyorder=self.settings.advanced_settings.filter_polyorder.value,
                normalization_mode={"No": 1, "Individual": 2, "Together": 3}[self.settings.output_settings.normalization_mode.value],
                use_cache=self.settings.advanced_settings.use_cache.value,
                catalyst_manager=self.catalyst_manager,
                callback_function=self.callback,
                error_function=self.error
            )

            # Once the analysis is complete, update the GUI
            self.update_gui_after_analysis(filtered_mz_values, filtered_results, unnormalized_ligand_curves)
        except Exception as e:
            self.error(f"Error during analysis: {str(e)}", "log show")

    def update_gui_after_analysis(self, filtered_mz_values, filtered_results, unnormalized_ligand_curves):
        #TODO: Victor du hast jetzt unnormalized_ligand_curves
        self.graph_frame.pack()

        datagrapher = grapher.DataGrapher("Scan Number", "Intensity")

        for i, ligand in enumerate(self.ligand):

            self.upload_frame.pack_forget()
            self.result_frame.pack_forget()
            self.analyze_frame.pack_forget()
            self.modi_frame.pack_forget()
            #self.select_mode_frame.pack_forget()
            self.output_frame.pack_forget()

            figure = plt.Figure(figsize=(6, 4), dpi=100)

            # Increase space between subplots for title
            figure.subplots_adjust(hspace=1.0, top=0.85)

            x_axis = list(range(int(self.entry_start_x_analysis.get()), int(int(self.entry_start_x_analysis.get()) + len(self.protein))))
            datagrapher.plot_graph(x_axis, self.protein, figure, 211, mz_value=self.settings.general_settings.protein_mz.value, y_axis=[0, max(self.protein) * 1.05])
            datagrapher.plot_graph(x_axis, ligand, figure, 212, mz_value=filtered_mz_values[i], y_axis=[0, max(ligand) * 1.05])

            # Add a display of the pearson and DTW values (similarity score) in the GUI
            figure.suptitle(f"Pearson similarity: {round(filtered_results[i][2]*100,2)}%   DTW score: {round(filtered_results[i][1], 2)}")
            #self.generate_pdf([self.protein[1]], [i[1]])
            self.ligand_figures.append(figure)
            #print(np.array(filtered_mz_values[i]))

        if not self.next_fig:
            self.next_fig = tk.Button(self.graph_frame, text="->", command=lambda: self.iterate_graph(1))
            self.next_fig.pack(side="right")
        if not self.previous_fig:
            self.previous_fig = tk.Button(self.graph_frame, text="<-", command=lambda: self.iterate_graph(-1))
            self.previous_fig.pack(side="left")

        self.show_graphs(0)

        messagebox.showinfo("Analysis complete", "Analysis completed successfully!")

        # Format strings of imported scan time and current analysis time
        string_scan_date = self.scan_date[4::].replace(" ", "_").replace(":", "-")
        string_analysis_date = datetime.now().strftime("%b_%d_%H-%M")

        # Create new directory for this scan's output
        output_directory = os.path.join(str(self.settings.output_settings.output_folder.value), "Scan_" + string_scan_date + "_Analysis_" + string_analysis_date)
        if os.path.exists(output_directory):
            output_directory = output_directory + " (1)"
        i = 2
        while os.path.exists(output_directory):
            output_directory = output_directory[:-4]
            output_directory = output_directory + f" ({i})"
            i += 1
        os.mkdir(output_directory)

        pdf_path = os.path.join(output_directory, "scan_" + string_scan_date + ".pdf")

        if not self.pdf_button:
            self.pdf_button = tk.Button(self.graph_frame, text="Open pdf", command=lambda: webbrowser.open(pdf_path), state = tk.DISABLED)
            self.pdf_button.pack(side="bottom", pady=2)
        else:
            self.pdf_button.config(command=lambda: webbrowser.open(pdf_path))
            self.pdf_button.config(state = tk.DISABLED)

        if not self.exit_button:
            self.exit_button= tk.Button(self.graph_frame, text="Go back", command=lambda: self.go_back())
            self.exit_button.pack(side="bottom", pady=2)

        # Generate CSV files if wanted
        if self.csv_choice.get() == "YES":
            for i in range(len(self.ligand)):
                generateCSV(output_directory, string_scan_date, i + 1, self.ligand[i], filtered_mz_values[i], start_scan=int(self.entry_start_x_analysis.get()))
            generateCSV(output_directory, string_scan_date, 0, self.protein, self.settings.general_settings.protein_mz.value, start_scan=int(self.entry_start_x_analysis.get()))

        # Generate settings file
        try:
            # self.store_fields_in_settings()
            self.catalyst_manager.export_settings(self.settings, output_directory)
        except Exception as e:
            self.error(str(e), "log")

        # Generate PDF with single/double plots
        single_plot = self.settings.output_settings.graph_combination.value == "One plot"
        generate_PDF(output_directory, self.scan_date[4::], self.settings, self.protein, self.settings.general_settings.protein_mz.value, 
                     self.ligand, filtered_mz_values, filtered_results,
                    single_plot=single_plot, normalized = not self.settings.output_settings.normalization_mode.value == 'No',
                    x_axis=list(range(int(self.entry_start_x_analysis.get()),
                                                                  int(int(self.entry_start_x_analysis.get()) + len(self.protein)))))
        self.pdf_button.config(state = tk.NORMAL)

    def show_error(self, message):
        """
            Opens error window to show message.
        """
        messagebox.showerror("Error", message)
        self.analyze_button.config(state=tk.NORMAL)

    def show_graphs(self, figure_counter):
        """
            Packs the figure on the GUI.
        """
        self.canvas_widget = FigureCanvasTkAgg(self.ligand_figures[figure_counter], self.graph_frame).get_tk_widget()
        self.canvas_widget.pack()

    def iterate_graph(self, direction):
        """
            Selects the next graph and also clears the gui from the current graph.
        """
        if direction == -1:
            if self.figure_counter > 0:
                self.figure_counter = self.figure_counter - 1
            else:
                self.figure_counter= len(self.ligand_figures) - 1
        if direction == 1:
            if self.figure_counter < len(self.ligand_figures) - 1:
                self.figure_counter = self.figure_counter + 1
            else:
                self.figure_counter = 0
        self.canvas_widget.destroy()
        self.show_graphs(self.figure_counter)

    # 'Go back' button opens the beginning frames to start again
    #TODO: Go back needs to reset the grapher class.
    def go_back(self):
        self.graph_frame.pack_forget()
        self.canvas_widget.destroy()
        #self.select_mode_frame.pack()
        self.upload_frame.pack()
        self.output_frame.pack()
        self.modi_frame.grid()
        self.analyze_frame.pack()
        self.result_frame.pack()
        self.ligand_figures= []
        self.ligand = []
        self.protein = []
        self.figure_counter = 0
        self.analyze_button.config(state=tk.NORMAL)
        # Clear the result text box
        #self.delete_textinput(self.result_text)
