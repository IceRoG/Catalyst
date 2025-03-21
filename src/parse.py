import re
import threading
import time
import os
from collections import defaultdict
from multiprocessing.pool import Pool
from multiprocessing import cpu_count


def get_number_of_scans(filepath: str, callback_function):
    """
        Returns the number of scans in the file.

        Parameters:
            filepath (str): Path to the file.
            callback_function (function): Callback function to print text to the GUI or the log.

        Returns:
            int: Number of scans in the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If no scan number can be found in the file.
    """
    start_time = time.time()

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    # Regex to match `scan=`
    scan_regex = re.compile(r"scan=(\d+)")


    # Open the file in reverse order
    with open(filepath, 'rb') as file:
        file.seek(0, os.SEEK_END)  # Move to the end of the file
        position = file.tell()
        buffer_size = 8192  # Read in chunks

        while position > 0:
            # Calculate chunk size
            read_size = min(buffer_size, position)
            position -= read_size
            file.seek(position)
            chunk = file.read(read_size).decode('utf-8', errors='ignore')

            # Process lines in reverse order
            for line in reversed(chunk.splitlines()):
                match = scan_regex.search(line)
                if match:
                    scan_number = int(match.group(1))
                    callback_function(f"Number of scans in the file: {scan_number}", "log")
                    callback_function(f"Time taken to get number of scans: {time.time() - start_time:.2f} seconds.", "log")
                    return scan_number

        # If no match is found, raise an error
        raise ValueError("No 'scan=' information found in the file.")

def get_max_and_min_mz(filepath: str, callback_function):
    """
        Returns the maximum and minimum m/z values in the file by processing only a percentage of lines.

        Parameters:
            filepath (str): Path to the file.
            callback_function (function): Callback function to print text to the GUI or the log.

        Returns:
            Tuple containing the maximum and minimum m/z values.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If no usable data can be found in the file.
    """
    start_time = time.time()

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    max_mz = float('-inf')
    min_mz = float('inf')

    with open(filepath, 'r') as file:
        previous_line = ""
        previous_line_digit = False
        s_present = True

        for line in file:
            # Check if the current line starts with 'S' and check for max m/z value of previous scan
            if previous_line_digit and line.startswith('S'):
                max_mz = max(max_mz, float(previous_line.split()[0]))

                s_present = True
                previous_line_digit = False
                previous_line = line
                continue

            # Check if current line is first value of a scan for min m/z value
            if s_present and previous_line.startswith('I'):
                previous_line_digit = line[0].isdigit()
                if previous_line_digit:
                    min_mz = min(min_mz, float(line.split()[0]))
                    s_present = False

            # Keep track of the previous line
            previous_line = line

    if min_mz == float('inf') and max_mz == float('-inf'):
        raise ValueError("No usable data found.")

    callback_function(f"Max m/z: {max_mz}.", "log")
    callback_function(f"Min m/z: {min_mz}.", "log")
    callback_function(f"Time taken to get max and min m/z values: {time.time() - start_time:.2f} seconds.", "log")

    return max_mz, min_mz

def process_chunk(scan_chunk: list, radius: float, start_value: float, end_value: float):
    """
        Returns the intensity over time for mass/charge areas with a width of 2*radius from start_value to end_value for given scans.

        Parameters:
            scan_chunk (list): List of scans (tuple of scan number and list of tuples with mass/charge and intensity) for which to compute the area timelines.
            radius (float): 2*radius is width of mass/charge areas. Minimal value is 0.01.
            start_value (float): Lower limit for the starting point of the first mass/charge area (included).
            end_value (float): Upper limit for the starting point of the last mass/charge area (excluded).
        Returns:
            Dictionary of List with sum  of intensity over time for each mass/charge area for given scans.

        Example output:
            {
                mass/charge_area1:  [[scan number, sumIntensityScan1, measurementCountScan1], [scan number, sumIntensityScan2, measurementCountScan2], ...],
                mass/charge_area2:  [[scan number, sumIntensityScan1, measurementCountScan1], [scan number, sumIntensityScan2, measurementCountScan2], ...],
                ...
            }
    """
    start_time = time.time()

    # Assure radius is not bigger than 0.01
    radius = max(radius, 0.01)

    # Dictionary to save timelines of all mass/charge areas
    local_timelines = defaultdict(list)

    # Compute timelines for given scans

    for scan_id, values in scan_chunk:
        for mass, intensity in values:
            # Compute mass/charge area center
            i = round((mass - start_value) / (2 * radius))
            area_center = round(start_value + 2 * i * radius, 2)

            if start_value <= area_center < end_value:
                if len(local_timelines[area_center]) < scan_id:
                    local_timelines[area_center].append([scan_id, intensity, 1])
                else:
                    local_timelines[area_center][-1][1] += intensity
                    local_timelines[area_center][-1][2] += 1

        # Add zero values to areas without values in this scan
        for area in local_timelines:
            if len(local_timelines[area]) < scan_id:
                local_timelines[area].append([scan_id, 0, 0])

    message = f"Process {threading.get_ident()}: Finished processing a chunk with {len(scan_chunk)} scans in {time.time() - start_time:.2f} seconds."

    return dict(local_timelines), message

class TextFileReader:
    """
        Class to read and process data from a text file.
        If you want to process a new file, you must create a new instance of this class.
    """
    def __init__(self, file_path: str, catalyst_manager, callback_function, error_function):
        """
            Class to analyse the file given by file_path.

            Parameters:
                file_path (str): Path of the file to analyse.
                catalyst_manager (CATALYST_manager): DASM_dir object that manages the CATALYST directory.
                callback_function (function): Callback function to print text to the GUI or the log.
                error_function (function): Callback function to print errors to the GUI or the log.

            Returns:
                Instance of the class.
        """
        self.FILE_PATH = file_path
        self.CATALYST_MANAGER = catalyst_manager
        """DO NOT MODIFY THIS VARIABLES"""

        # Remove the file extension
        self.filename_without_extension = os.path.splitext(os.path.basename(self.FILE_PATH))[0]

        # File data
        self.FILE_CONTENT = None
        self.CreationDate = None
        self.function = None
        self.min_mz = None
        self.max_mz = None

        self.CallbackFunction = callback_function
        self.ErrorFunction = error_function

    def _read_content(self, function: int):
        """
            Returns the content of the file given by self.FILE_PATH for a given function and sets the min/max m_z value for this file.

            Parameters:
                function (int): Number of the function to read from file.

            Returns:
                Dictionaries of Lists: {scan_number: [(mass/charge, intensity),(mass/charge, intensity), ...], ...} for given function number.
        """
        try:
            # Read file from self.FILE_PATH
            self.FILE_CONTENT = self._parse(function=function)
            self.function = function

            # Store min and max m_z value appearing in the file for the given function
            self.max_mz, self.min_mz = get_max_and_min_mz(self.FILE_PATH, self.CallbackFunction)
        except FileNotFoundError:
            #raise FileNotFoundError(f"The file '{self.FILE_PATH}' was not found.")
            self.ErrorFunction(f"The file '{self.FILE_PATH}' was not found.", "log show")
        except IOError as e:
            #raise IOError(f"An issue occurred while reading '{self.FILE_PATH}'.\n{type(e).__name__}: {e}")
            self.ErrorFunction(f"An issue occurred while reading '{self.FILE_PATH}'.\n{type(e).__name__}: {e}", "log show")

    def get_intensity_timeline(self, m_z: float, area_range: float, function: int,use_cache: bool):
        """
            Returns the intensity over time for a given mass/charge (m/z).
            Values are averaged around the m/z by a radius of area_range/2.
            The cache use (loading/storing) can be toggled.

            Parameters:
                m_z (float): Mass/charge value for which to retrieve intensity over time.
                area_range (float): Range of the mass/charge area to collect and average data from.
                function (int): Function number of the data to analyze.
                use_cache (bool): Flag to enable/disable caching.

            Returns:
                List of intensity values over time for the given mass/charge. Position i in the list corresponds to scan i+1.
        """
        self.CallbackFunction(f"Calculating intensity timeline for {m_z} m/z...", "log print")

        if use_cache:
            cached_timeline, creation_date = self.CATALYST_MANAGER.load_timeline_from_cache(self.filename_without_extension, area_range, function, m_z)

            if cached_timeline:
                self.CallbackFunction("Cache hit. Returning cached timeline.", "log print")
                self.CreationDate = creation_date
                return cached_timeline
            else:
                self.CallbackFunction("Cache miss. Starting processing data.", "log print")
        else:
            self.CallbackFunction("Cache disabled. Starting processing data.", "log print")

        # If the file has not been processed, start the processing
        if not self.FILE_CONTENT or self.function != function:
            self._read_content(function)

        radius = area_range / 2

        # Ensure that the mz value exists in the file content by checking the min and max values in the file content
        if not (self.min_mz - radius <= m_z <= self.max_mz + radius):
            raise ValueError(f"No data for given mass/charge value {m_z} in file.")

        # List to store intensity over time for the given m/z
        timeline = []

        # Otherwise, process the m/z data from the file content
        for scan_id, values in self.FILE_CONTENT.items():
            sum_values_in_radius = 0
            values_in_radius = 0

            # Retrieve all values in the radius around m/z
            # Use get_bin method if available
            data = next(((m, intensity) for m, intensity in values if m_z - radius <= m < m_z + radius), None)
            if data is not None:
                index = values.index(data)
                while values[index][0] < m_z + radius:
                    sum_values_in_radius += values[index][1]
                    values_in_radius += 1
                    index += 1

            # Compute the average intensity for this scan or 0 if no values were in radius
            average_intensity = round(sum_values_in_radius / values_in_radius, 5) if values_in_radius > 0 else 0

            # Save the average intensity for this scan
            timeline.append(average_intensity)

        self.CallbackFunction(f"Intensity timeline for {m_z} m/z created.", "log print")

        # Cache timeline if enabled
        if use_cache:
            self.CATALYST_MANAGER.save_timeline_cache(self.filename_without_extension, function, area_range, m_z, timeline, self.CreationDate)

        return timeline

    def get_all_intensity_timelines(self, area_range: float, start_value: float, end_value: float, function: int, num_processes: int, use_cache: bool):
        """
            Returns the intensity over time for mass/charge areas with a width of 2*radius from start_value to end_value for given function.
            This function also caches the results in a file in the cache folder if caching is enabled.

            Parameters:
                area_range (float): Range of the mass/charge areas.
                start_value (float): Lower limit for the starting point of the first mass/charge area (included).
                end_value (float): Upper limit for the starting point of the last mass/charge area (excluded).
                function (int): Function number to analyze from data.
                num_processes (int): Number of processes to use.
                use_cache (bool): Flag to enable/disable caching.

            Returns:
                Dictionary of lists with intensity over time for each mass/charge area for given function.
        """
        start_time = time.time()
        self.CallbackFunction(f"Calculating all intensity timelines for {self.FILE_PATH}...", "log print")

        # Check if the file has already been processed and load results instead of calculating
        if use_cache:
            cached_timelines, creation_date = self.CATALYST_MANAGER.load_timelines_from_cache(self.filename_without_extension, area_range, function, start_value, end_value)

            if cached_timelines:
                self.CallbackFunction("Cache hit. Returning cached timelines.", "log print")
                self.CreationDate = creation_date
                return cached_timelines
            else:
                self.CallbackFunction("Cache miss. Starting processing data.", "log print")
        else:
            self.CallbackFunction("Cache disabled. Starting processing data.", "log print")

        # If the file has not been processed, start the processing
        if not self.FILE_CONTENT or self.function != function:
            self._read_content(function)

        radius = area_range / 2

        # Ensure that the mz value exists in the file content by checking the min and max values in the file content
        if self.max_mz < start_value - radius or self.min_mz > end_value + radius:
            raise ValueError("No data for given m/z region in file.")

        # Assure not to many processes are started
        num_processes = min(num_processes, cpu_count() - 2)

        # Prepare values for analyses
        scans = list(self.FILE_CONTENT.items())
        scans_length = len(scans)
        chunk_size = max(1, scans_length // num_processes)

        # List of lists of tuples with format (scan_number, [(mass/charge, intensity),(mass/charge, intensity), ...]), forms chunks to distribute to processes
        scan_chunks = [scans[i * chunk_size: (i + 1) * chunk_size] for i in range(num_processes - 1)]
        scan_chunks.append(scans[(num_processes - 1) * chunk_size: scans_length])

        del scans

        # Compute sum of mass/charge areas for given scan chunks
        if num_processes > 1: # Multi-process
            self.CallbackFunction(f"Starting {num_processes} processes to calculate timelines...", "log print")
            with Pool(processes=num_processes) as pool:
                results = pool.starmap(process_chunk, [(chunk, radius, start_value, end_value) for chunk in scan_chunks])
        else: # Only use this process
            self.CallbackFunction(f"Starting {num_processes} process to calculate timelines...", "log print")
            results = (process_chunk(chunk, radius, start_value, end_value) for chunk in scan_chunks)

        del scan_chunks

        results, messages = zip(*results)

        for message in messages:
            self.CallbackFunction(message, "log print")

        # Dictionary for complete timeline of mass/charge areas with lambda as default value for un-initialized keys (mass/charge areas)
        all_timelines = defaultdict(lambda: [[0, 0] for _ in range(scans_length)])

        self.CallbackFunction("Combining chunks into complete timelines...", "log print")

        # Combine timelines from all scan chunks
        # Result contains all local timelines of a chunk as a dictionary with mass/charge as key and data is a list of lists (inner lists are [sumIntensity, amountMeasurements], index in list is can number)
        for result in results:
            for area, intensity_list in result.items():
                for scan_nr, intensity_sum, count in intensity_list:
                    all_timelines[area][scan_nr - 1][0] += intensity_sum
                    all_timelines[area][scan_nr - 1][1] += count

        del results

        # Dictionary to save timelines of all mass/charge areas
        cached_timelines = {}

        for area in all_timelines:
            cached_timelines[str(area)] = [0 if scan[1] <= 0 else scan[0] / scan[1] for scan in all_timelines[area]]

        del all_timelines

        if use_cache:
            self.CATALYST_MANAGER.save_timelines_cache(self.filename_without_extension, function, area_range, start_value, end_value, cached_timelines, self.CreationDate)

        self.CallbackFunction("All intensity timelines created.", "log print")
        self.CallbackFunction(f"Processing time: {time.time() - start_time:.2f} seconds.", "log print")
        return cached_timelines

    def _parse(self, function: int):
        """
            Parse an .ms1/.txt file and return a tuple of two dictionary with the scan number as key and a list of (m/z, intensity) tuples.

            Parameters:
                function (int): Number of the function to read from file.

            Returns:
                Dictionary of Lists: {scan_number: [(mass/charge, intensity),(mass/charge, intensity), ...], ...} for the given function.

            Example:
                {1: [(100.0, 2000), (101.0, 2100), (102.0, 1900)], 2: [...], ...}
        """
        self.CallbackFunction(f"Start parsing file at '{self.FILE_PATH}'.", "log print")
        start_time = time.time()

        selected_function_data = {}

        # Variables to cache data while parsing a scan and save it after finishing the scan
        current_function = None
        current_scan = None
        current_data = []

        def save_scan_data():
            """Helper function to save current scan data if it matches the specified function."""
            if current_function == function:
                selected_function_data[current_scan] = current_data[:]

        # Regex for detecting metadata efficiently
        function_scan_regex = re.compile(r"function=(\d+)|scan=(\d+)")

        # Open file from self.FILE_PATH
        with open(self.FILE_PATH, 'r') as file:
            for line in file:
                first_char = line[0]
                if first_char.isdigit():  # Data line, most frequent case
                    if current_function == function:
                        # Parsing of mass and intensity
                        mass, intensity = line.split(maxsplit=1)
                        current_data.append((float(mass), float(intensity)))

                elif first_char == 'S':  # Scan boundary
                    if current_function == function and current_scan is not None:
                        save_scan_data()  # Save the previous scan's data

                    # Reset scan data
                    current_function = None
                    current_scan = None
                    current_data.clear()

                elif first_char == 'I':  # Metadata, only after a scan boundary
                    # Extract metadata with regex
                    for match in function_scan_regex.findall(line):
                        if match[0]:  # function=
                            current_function = int(match[0])
                        elif match[1]:  # scan=
                            current_scan = int(match[1])
                elif first_char == 'H':  # Header, only at the beginning of the file
                    # Extract creation date
                    if "CreationDate" in line:
                        self.CreationDate = line.split("CreationDate", maxsplit=1)[1].strip()

            # Save the last scan
            if current_function and current_scan:
                save_scan_data()

        self.CallbackFunction(f"Finished parsing in {time.time() - start_time:.2f} seconds.", "log print")

        return selected_function_data
