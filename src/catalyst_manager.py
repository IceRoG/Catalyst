import os
import shutil
import time
import zipfile
from src.settings.settings import Settings

class CATALYST_manager:
    """
        Class to manage the catalyst directory.
    """
    def __init__(self, catalyst_path: str = "PROGRAMDATA", callback_function = None, error_function = None, cache_threshold: float = 2.0,  log_threshold: float = 0.01):
        """
            Class to manage the catalyst directory.

            Parameters:
                catalyst_path (str): Path to CATALYST-folder is being created. Default ist 'PROGRAMDATA'.
                callback_function (function): Callback function to print text to the GUI or the log. Default is None.
                error_function (function): Callback function to print errors to the GUI or the log. Default is None
                cache_threshold (float): Maximum size the cache can get in GB. Default is 2.0.
                log_threshold (float): Maximum size the log can get in GB. Default is 1.0.

            Returns:
                Instance of the class.
        """
        self.FOLDER_PATH = f"{os.getenv('PROGRAMDATA')}\\CATALYST" if catalyst_path == "PROGRAMDATA" else catalyst_path
        self.CACHE_PATH = f"{self.FOLDER_PATH}\\cache"
        self.LOG_PATH = f"{self.FOLDER_PATH}\\catalyst.log"
        self.SETTINGS_PATH = f"{self.FOLDER_PATH}\\settings.txt"

        self.cache_threshold = max(cache_threshold, 0.0)
        self.log_threshold = max(log_threshold, 0.0)
        self.CallbackFunction = callback_function
        self.ErrorFunction = error_function

        self.SETTINGS_VERSION = "1.2"

        self.cache_size = 0.0
        self.cache_size_valid = False

        self.messages = []

        # Ensures CATALYST and cache directories exist. Log file is handled by logging class.
        if not os.path.exists(self.CACHE_PATH):
            os.makedirs(self.CACHE_PATH)
            self.messages.append(("Callback", "Cache directory created.", "log"))

        if self.cache_threshold != cache_threshold:
            self.messages.append(("Callback", "Parameter 'cache_threshold' can not be smaller then zero. Set to '0.0'.", "log print"))

        if self.log_threshold != log_threshold:
            self.messages.append(("Callback", "Parameter 'log_threshold' can not be smaller then zero. Set to '0.0'.", "log print"))


    def set_cache_threshold(self, cache_threshold: float):
        """
            Set cache threshold and check if the cache still meets the size requirement.

            Parameters:
                cache_threshold (float): Maximum size the cache can get in GB.
        """
        self.cache_threshold = max(cache_threshold, 0.0)
        if self.cache_threshold != cache_threshold:
            self.CallbackFunction("Parameter 'cache_threshold' can not be negative.", "log")
        self.CallbackFunction(f"New cache threshold is {self.cache_threshold} GB.", "log")
        self.check_cache()

    def set_log_threshold(self, log_threshold: float):
        """
            Set cache threshold and check if the log file still meets the size requirement.

            Parameters:
                log_threshold (float): Maximum size the log can get in GB.
        """
        self.log_threshold = max(log_threshold, 0.0)
        if self.log_threshold != log_threshold:
            self.CallbackFunction("Parameter 'log_threshold' can not be negative.", "log")
        self.CallbackFunction(f"New log threshold is {self.log_threshold} GB.", "log")
        self.check_log()

    def check(self):
        for functype, m, mtype in self.messages:
            if functype == "Callback":
                self.CallbackFunction(m, mtype)
            elif functype == "Error":
                self.ErrorFunction(m, mtype)

        return self.check_settings()

    def check_settings(self):

        if os.path.exists(self.SETTINGS_PATH):
            with open(self.SETTINGS_PATH, "r") as file:
                if f"CATALYST settings v{self.SETTINGS_VERSION}" in file.readline():
                    return self.load_settings_from_catalyst()
                self.CallbackFunction(f"Current CATALYST settings version outdated. Update settings to version {self.SETTINGS_VERSION}", "log")

        return self.create_default_settings()


    def create_default_settings(self):
        """
            Creates a settings file in the CATALYST directory.
        """
        default_settings = Settings()
        settings = default_settings.get_settings()

        with open(self.SETTINGS_PATH, "w") as file:
            file.write(f"CATALYST settings v{self.SETTINGS_VERSION}\n")
            for category, settings_list in settings:
                file.write(f"# {category}\n")
                for setting in settings_list:
                    file.write(f"{setting.name}={setting.value}\n")

        self.CallbackFunction(f"Default settings for version {self.SETTINGS_VERSION} created.", "log")
        return default_settings

    def load_settings_from_catalyst(self):
        """
            Returns the settings saved in the settings file from the CATALYST directory.
        """
        return self.import_settings(self.SETTINGS_PATH)

    def import_settings(self, file_path: str):
        """
            Creates a settings object with the settings in the given file.

            Parameters:
                file_path (str): Path to a settings file.

            Returns:
                Configured settings object.
        """
        self.CallbackFunction(f"Import settings from '{file_path}'.", "log")

        if not os.path.exists(file_path):
            raise ValueError(f"No file found at {file_path}. Keep current settings.")

        settings = Settings()

        with open(file_path, "r") as file:
            if not f"CATALYST settings v{self.SETTINGS_VERSION}" in file.readline():
                raise ValueError("Given file does not match current CATALYST settings version format. Keep current settings.")

            for line in file:
                if line.startswith("#"):
                    match line.split(" ", 1)[1].strip():
                        case "General settings":
                            setting_type_obj = settings.general_settings
                            pass

                        case "Targeted settings":
                            setting_type_obj = settings.targeted_settings
                            pass

                        case "Untargeted settings":
                            setting_type_obj = settings.untargeted_settings
                            pass

                        case "Output settings":
                            setting_type_obj = settings.output_settings
                            pass

                        case "Advanced settings":
                            setting_type_obj = settings.advanced_settings
                            pass

                    continue

                name, value = line.split("=")
                name = name.strip()
                value = value.strip()

                if not hasattr(setting_type_obj, name):
                    self.ErrorFunction(f"Wrong setting '{line}' in category '{setting_type_obj.__class__.__name__}'.", "log")
                    continue

                attribute = getattr(setting_type_obj, name)

                if value == "None":
                    attribute.value = None
                    continue

                if attribute.data_type == str:
                    attribute.value = value
                    continue

                if attribute.data_type == bool:
                    attribute.value = value == "True"
                    continue

                if attribute.data_type == float:
                    attribute.value = float(value)
                    continue

                if attribute.data_type == int:
                    attribute.value = int(value)
                    continue

        self.CallbackFunction("Settings imported.", "log")

        return settings

    def export_settings(self, settings: Settings, output_path: str):
        """
            Exports the settings in a txt file to the given path.

            Parameters:
                settings (Settings): Settings to export as a txt file.
                output_path (str): Path to save the zip file to.
        """
        output_file = os.path.join(output_path, f"catalyst_settings_{time.strftime("%Y-%m-%d_%H-%M-%S")}.txt")

        with open(output_file, 'w') as file:
            file.write(f"# CATALYST settings v{self.SETTINGS_VERSION}\n")
            for category, settings_list in settings.get_settings():
                file.write(f"# {category}\n")
                for setting in settings_list:
                    file.write(f"{setting.name}={setting.value}\n")

        self.CallbackFunction(f"Settings exported to '{output_path}'.", "log print")

    def fully_clear_cache(self):
        """
            Clears the cache directory.
        """
        for file in os.listdir(self.CACHE_PATH):
            file_path = os.path.join(self.CACHE_PATH, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                self.ErrorFunction(e, "log show")

        self.cache_size = 0.0
        self.cache_size_valid = True
        self.CallbackFunction("Cache cleared. New cache size: 0.00 GB.", "log")

    def import_cache(self, zip_path: str):
        """
            Extracts a zip folder to the cache.

            Parameters:
                zip_path (str): Path of the zip file.
        """
        if not os.path.isfile(zip_path):
            raise FileNotFoundError(f"No file at '{zip_path}' found.")

        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            zip_file.extractall(self.CACHE_PATH)

        self.CallbackFunction("Cache import completed.", "log print")


    def export_cache(self, output_path: str):
        """
            Exports cache in a zip file to the given path.

            Parameters:
                output_path (str): Path to save the zip file to.
        """
        output_zip = os.path.join(output_path, f"catalyst_cache_{time.strftime("%Y-%m-%d_%H-%M-%S")}.zip")

        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(self.CACHE_PATH):
                for file in files:
                    file_path = os.path.join(root, file)
                    zip_file.write(file_path, os.path.relpath(file_path, self.CACHE_PATH))

        self.CallbackFunction(f"Cache exported to '{output_path}'.", "log print")

    def remove_oldest_file(self):
        """
            Removes the oldest file in the cache directory.
        """
        files = [f for f in os.listdir(self.CACHE_PATH) if os.path.isfile(os.path.join(self.CACHE_PATH, f))]
        if files:
            oldest_file = min(files, key=lambda x: os.path.getctime(os.path.join(self.CACHE_PATH, x)))
            os.remove(os.path.join(self.CACHE_PATH, oldest_file))
            self.CallbackFunction(f"Oldest file '{oldest_file}' removed from cache.", "log")

        self.cache_size_valid = False

    def remove_oldest_files(self, num_files: int):
        """
            Removes the oldest num_files files in the cache directory.

            Parameters:
                num_files (str): The number of files to remove.
        """
        for _ in range(num_files):
            self.remove_oldest_file()

    def remove_largest_file(self):
        """
            Removes the largest file in the cache directory.
        """
        files = [f for f in os.listdir(self.CACHE_PATH) if os.path.isfile(os.path.join(self.CACHE_PATH, f))]
        if files:
            largest_file = max(files, key=lambda x: os.path.getsize(os.path.join(self.CACHE_PATH, x)))
            os.remove(os.path.join(self.CACHE_PATH, largest_file))
            self.CallbackFunction(f"Largest file '{largest_file}' removed from cache.", "log")

        self.cache_size_valid = False

    def remove_largest_files(self, num_files: int):
        """
            Removes the largest num_files files in the cache directory.

            Parameters:
                num_files (int): The number of files to remove.
        """
        for _ in range(num_files):
            self.remove_oldest_file()

    def remove_least_recently_used_file(self):
        """
            Removes the file in the cache folder that has not been used for the longest time.
        """
        oldest_file = None
        oldest_access_time = float('inf')

        for dir_path, dir_names, filenames in os.walk(self.CACHE_PATH):
            for f in filenames:
                file_path = os.path.join(dir_path, f)
                access_time = os.path.getatime(file_path)  # Get latest access
                if access_time < oldest_access_time:
                    oldest_access_time = access_time
                    oldest_file = file_path

        if oldest_file:
            os.remove(oldest_file)
            self.CallbackFunction(f"Least recently used file '{oldest_file}' removed from cache.", "log")

        self.cache_size_valid = False

    def remove_least_recently_used_files(self, num_files: int):
        """
            Removes the num_files files in the cache folder that has not been used for the longest time.

            Parameters:
                num_files (int): The number of files to remove.
        """
        for _ in range(num_files):
            self.remove_least_recently_used_file()

    def remove_oldest_lines(self, num_lines: int):
        """
            Removes the oldest num_lines lines in the log file.

            Parameters:
                num_lines (int): The number of lines to remove.
        """
        with open(self.LOG_PATH, "r+") as file:
            lines = file.readlines()
            new_lines = lines[num_lines:]

            file.seek(0)
            file.writelines(new_lines)
            file.truncate()

        self.CallbackFunction(f"Removed oldest {num_lines} lines from log to free space.", "log")

    def get_cache_size(self):
        """
            Calculate the total size of the cache directory in GB rounded to three decimal places.

            Returns:
                float: Total size of the cache directory in GB.
        """
        if self.cache_size_valid:
            return self.cache_size

        total_size = 0
        # Walk through all files and subdirectories in the given directory
        for dir_path, dir_names, filenames in os.walk(self.CACHE_PATH):
            for filename in filenames:
                file_path = os.path.join(dir_path, filename)
                # Add file size if it exists
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)

        # Convert size from bytes to gigabytes
        self.cache_size = round(total_size / (1024**3), 3)
        self.cache_size_valid = True

        return self.cache_size

    def get_log_size(self):
        """
            Calculate the total size of the log file in GB rounded to three decimal places.

            Returns:
                float: Total size of the cache directory in GB.
        """
        return round(os.path.getsize(self.LOG_PATH) / (1024**3), 3)

    def check_cache(self):
        """
            Check if the cache directory is larger than its threshold. Remove the oldest files until it has reached the threshold.

            Returns:
                False if the cache was too big and files were removed, true otherwise.
        """
        cache_size = self.get_cache_size()
        self.CallbackFunction(f"Checking cache size. Current cache size: {cache_size} GB.", "log")

        # Check if cache size is smaller then threshold
        if cache_size <= self.cache_threshold:
            return True

        # Remove the oldest files until the cache size is less than the threshold
        while cache_size > self.cache_threshold:
            self.remove_least_recently_used_file()
            cache_size = self.get_cache_size()

        self.CallbackFunction(f"Cache size exceeded threshold value. New cache size: {cache_size} GB.", "log")

        return False

    def check_log(self):
        """
            Check if the cache directory is larger than its threshold. Remove the oldest files until it has reached the new threshold.


            Returns:
                False if the log file was too big and lines were removed, True otherwise.
        """
        log_size = self.get_log_size()
        self.CallbackFunction(f"Checking log size. Current log size: {log_size} GB.", "log")

        # Check if log size is smaller then threshold
        if log_size <= self.log_threshold:
            return True

        # Remove the oldest lines until the log size is less than the threshold
        while log_size > self.log_threshold:
            self.remove_oldest_lines(1000)
            log_size = self.get_log_size()

        self.CallbackFunction(f"Log size exceeded threshold value. New log size: {log_size} GB.", "log")

        return False

    def load_timeline_from_cache(self, data_file_name: str, area_range: float, function: int, m_z: float):
        """
            Search the intensity timeline for given parameters in the cache.

            Parameters:
                data_file_name (str): Name of the file.
                area_range (float): Range of the mass/charge area.
                function (int): Function identifier.
                m_z (float): Mass/charge value for which to retrieve intensity over time.

            Returns:
                Tuple of timeline and creation date.
                Both None if no fitting timeline was cached.
        """
        start_time = time.time()

        for filename in os.listdir(self.CACHE_PATH):
            if filename.startswith(data_file_name):
                try:
                    # Check if the file matches "_single" format
                    if filename.endswith("_single.catalyst"):
                        # Parse "_single" file
                        parts = filename.replace(".catalyst", "").split("_")
                        file_function = int(parts[-4][1:])  # Extract function (e.g., f1 -> 1)
                        file_range = float(parts[-3][1:])  # Extract range (e.g., r10 -> 10)
                        file_m_z = float(parts[-2][2:])  # Extract m/z (e.g., mz100 -> 100)

                        if file_function == function and file_range == area_range and file_m_z == m_z:
                            # Load cached file
                            with open(os.path.join(self.CACHE_PATH, filename), "r") as file:
                                creation_date = file.readline().strip()
                                for line in file:
                                    timeline = [float(value) for value in line[1:-2].split(", ")]
                            self.CallbackFunction(f"File {filename} loaded from cache.", "log")
                            self.CallbackFunction(f"Time taken: {time.time() - start_time:.2f} seconds.", "log")
                            return timeline, creation_date
                except (IndexError, ValueError):
                    continue  # Skip files that don't match the expected format

        return None, None

    def load_timelines_from_cache(self, data_file_name: str, area_range: float, function: int, start_value: float, end_value: float):
        """
            Search the intensity timelines for given parameters in the cache.

            Parameters:
                data_file_name (str): Name of the data file.
                area_range (float): Range of the mass/charge area.
                function (int): Function identifier.
                start_value (float): Start value of the m/z range.
                end_value (float): End value of the m/z range.

            Returns:
                Tuple of timelines and creation date.
                Both None if no fitting timelines were cached.
        """
        all_timelines_avg = {}
        start_time = time.time()


        for filename in os.listdir(self.CACHE_PATH):
            if filename.startswith(data_file_name):
                try:
                    # Check if the file matches "_multiple" format
                    if filename.endswith("_multiple.catalyst"):
                        # Parse "_multiple" file
                        parts = filename.replace(".catalyst", "").split("_")
                        file_function = int(parts[-5][1:])  # Extract function (e.g., f1 -> 1)
                        file_range = float(parts[-4][1:])  # Extract range (e.g., r10 -> 10)
                        file_start_value = float(parts[-3][2:])  # Extract start value (e.g., sv20 -> 20)
                        file_end_value = float(parts[-2][2:])  # Extract end value (e.g., ev50 -> 50)

                        if file_function == function and file_range == area_range and start_value >= file_start_value and end_value <= file_end_value:
                            # Load cached file
                            with open(os.path.join(self.CACHE_PATH, filename), "r") as file:
                                creation_date = file.readline().strip()
                                for line in file:
                                    area, values = line.split(": ")
                                    all_timelines_avg[area] = [float(value) for value in values[1:-2].split(", ")]
                            self.CallbackFunction(f"File {filename} loaded from cache.", "log")
                            self.CallbackFunction(f"Time taken: {time.time() - start_time:.2f} seconds.", "log")
                            return all_timelines_avg, creation_date

                except (IndexError, ValueError):
                    continue  # Skip files that don't match the expected format

        return None, None

    def save_timeline_cache(self, data_file_name: str, function: int, area_range: float, m_z: float, timeline_data: list, creation_date: str):
        """
            Save a single timeline to the cache.

            Parameters:
                data_file_name (str): Name of the data file.
                function (int): Function identifier.
                area_range (float): Range of the mass/charge area.
                m_z (float): Mass/charge value.
                timeline_data (list): Timeline data to save.
                creation_date (str): Creation date of the data.
        """
        filename = f"{data_file_name}_f{function}_r{area_range}_mz{m_z}_single.catalyst"
        filepath = os.path.join(self.CACHE_PATH, filename)

        with open(filepath, "w") as file:
            file.write(f"{creation_date}\n")
            values = [round(value, 2) for value in timeline_data]  # Round values to 2 decimal places
            file.write(f"{values}\n")

        self.CallbackFunction(f"File {filename} saved in cache.", "log")

        # Check the check to make sure the cache does not exceed its threshold
        self.check_cache()

    def save_timelines_cache(self, data_file_name: str, function: int, area_range: float, start_value: float, end_value: float, timeline_data: dict, creation_date: str):
        """
            Save multiple timelines to the cache.

            Parameters:
                data_file_name (str): Name of the data file.
                function (int): Function identifier.
                area_range (float): Range of the mass/charge area.
                start_value (float): Start of the mass/charge range.
                end_value (float): End of the mass/charge range.
                timeline_data (dict): Timeline data to save.
                creation_date (str): Creation date of the data.
        """

        filename = f"{data_file_name}_f{function}_r{area_range}_sv{start_value}_ev{end_value}_multiple.catalyst"
        filepath = os.path.join(self.CACHE_PATH, filename)

        with open(filepath, "w") as file:
            file.write(f"{creation_date}\n")
            for area, values in timeline_data.items():
                values = [round(value, 2) for value in values]  # Round values to 2 decimal places
                file.write(f"{area}: {values}\n")

        self.CallbackFunction(f"File {filename} saved in cache.", "log")

        # Check the check to make sure the cache does not exceed its threshold
        self.check_cache()
