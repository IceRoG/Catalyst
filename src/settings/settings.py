from src.settings.setting import Setting

class General_settings:

    def __init__(self):
        self.data_path = Setting("data_path", "Data file path", None, str)

        self.protein_mz = Setting("protein_mz", "Protein m/z", None, float)
        self.protein_charge_state = Setting("protein_charge_state", "Protein charge state", None, int)
        self.function_protein = Setting("function_protein", "Energy function protein", 2, int)
        self.function_ligand = Setting("function_ligand", "Energy function ligands", 2, int)

        self.protein_sampling_range = Setting("protein_sampling_range", "Protein sampling range", 4.0, float)
        self.ligand_sampling_range = Setting("ligand_sampling_range", "Ligand sampling range", 0.04, float)

        self.dtw_threshold = Setting("dtw_threshold", "DTW threshold", 10.0, float)
        self.pearson_threshold = Setting("pearson_threshold", "Pearson threshold", 0.87, float)

        self.analysis_start = Setting("analysis_start", "Analysis scan-start", 1, int)
        self.analysis_end = Setting("analysis_end", "Analysis scan-end", 100, int)

        self.analysis_mode = Setting("analysis_mode", "Analysis mode", "Targeted", str)

    def get_settings(self):
        """
            Returns tuple of setting name and list of settings with format ("General settings", [setting, ...]).
        """
        return "General settings", list(self.__dict__.values())

class Targeted_settings:

    def __init__(self):
        self.ligands_path = Setting("ligands_path", "Ligand file path", None, str)

    def get_settings(self):
        """
            Returns tuple of setting name and list of settings with format ("Targeted settings", [setting, ...]).
        """
        return "Targeted settings", list(self.__dict__.values())

class Untargeted_settings:

    def __init__(self):
        self.charge_state_exclusion = Setting("charge_state_exclusion", "Protein charge state exclusion range", 3, int)
        self.start_mz = Setting("start_mz", "Start m/z", 50.0, float)
        self.end_mz = Setting("end_mz", "End m/z", 8000.0, float)
        self.ligand_group_range = Setting("ligand_group_range", "Ligand m/z grouping range", 1.0, float)
        self.protein_exclusion_window = Setting("protein_exclusion_window", "Protein exclusion window", 5.0, float)

    def get_settings(self):
        """
            Returns tuple of setting name and list of settings with format ("Untargeted settings", [setting, ...]).
        """
        return "Untargeted settings", list(self.__dict__.values())

class Output_settings:

    def __init__(self):
        self.output_folder = Setting("output_folder", "Output folder path", None, str)
        self.normalization_mode = Setting("normalization_mode", "Normalization Mode", "Individual", str)
        self.graph_combination = Setting("graph_combination", "Protein & Ligand graphs in", "One plot", str)
        self.csv_files = Setting("csv_files", "Create csv files", True, bool)

    def get_settings(self):
        """
            Returns tuple of setting name and list of settings with format ("Output settings", [setting, ...]).
        """
        return "Output settings", list(self.__dict__.values())

class Advanced_settings:

    def __init__(self):
        self.charge_state_sum = Setting("charge_state_sum", "Protein charge state sum range", 0, int)
        self.filter_window = Setting("filter_window", "Savitzky-Golay filter window length", 5, int)
        self.filter_polyorder = Setting("filter_polyorder", "Savitzky-Golay filter polyorder", 3, int)
        self.parse_processes = Setting("parse_processes", "Num of parse processes", 1, int)
        self.analysis_processes = Setting("analysis_processes", "Num of analysis processes", 4, int)
        self.cache_size = Setting("cache_size", "Max cache size (GB)", 2.0, float)
        self.use_cache = Setting("use_cache", "Use cache", True, bool)

    def get_settings(self):
        """
            Returns tuple of setting name and list of settings with format ("Advanced settings", [setting, ...]).
        """
        return "Advanced settings", list(self.__dict__.values())

class Settings:

    def __init__(self):
        self.general_settings = General_settings()
        self.targeted_settings = Targeted_settings()
        self.untargeted_settings = Untargeted_settings()
        self.output_settings = Output_settings()
        self.advanced_settings = Advanced_settings()

    def get_settings(self):
        """
            Returns list of tuples with all attributes with format [(setting name, [setting, ...]), ...].
        """
        return [attr.get_settings() for attr in self.__dict__.values()]
