import time
import numpy as np

from src.data_analysis.analyzer import CurveSimilarityDetector, group_and_filter_results, normalize_curve
from src.parse import TextFileReader

def analyze_targeted(file_path, catalyst_manager, ligand_mz_values, dtw_threshold=12, pearson_threshold=0.85,
                     window_length=5, polyorder=3, protein_mz_value=0, range_ligand=0.02, range_protein=0.02,
                     function_ligand=2, function_protein=2, use_savgol=True, use_cache=True, start_x_axis=None, end_x_axis=None,
                     protein_charge_state=0, protein_charge_state_averaging_window=0, callback_function=None, error_function = None, normalization_mode = 0):
    #TODO: Update documentation
    """
    Analyze targeted ligand curves and return detailed results.

    Args:
        file_path (str): Path to the input file.
        catalyst_manager (CATALYST_manager): Manages the CATALYST directory.
        ligand_mz_values (list): List of m/z values for the ligands.
        dtw_threshold (float): Threshold for Dynamic Time Warping (DTW) distance.
        pearson_threshold (float): Threshold for Pearson correlation.
        window_length (int): Window length for smoothing.
        polyorder (int): Polynomial order for smoothing.
        protein_mz_value (float): m/z value for the protein curve.
        range_ligand (float): Range for binning m/z values for ligand curves.
        range_protein (float): Range for binning m/z values for protein curve.
        function_ligand (int): Function to use for binning m/z values for ligand curves.
        function_protein (int): Function to use for binning m/z values for protein curve.
        use_savgol (bool): Flag to use Savitzky-Golay filter for smoothing.
        use_cache (bool): Flag to use cache for storing the intensity values.
        start_x_axis (int or None): Start time which to use for the analysis
        end_x_axis (int or None): End time which to use for the analysis
        protein_charge_state (int): Charge state of the protein for averaging.
        protein_charge_state_averaging_window (int): Window for averaging the protein charge state.
        callback_function (function): Callback function to print text to the GUI.
        error_function (function): Callback function to print error messages to the GUI.
        normalization_mode (int): Mode for normalization. 0: No normalization, 1: All ligands are normalized individually , 2: All ligands are normalized together.
    Returns:
        list: A list of tuples containing (m/z value, ligand curve, is_similar, DTW score, Pearson score).
    """
    # Initialize the parser class
    parser = TextFileReader(file_path=file_path, catalyst_manager=catalyst_manager, callback_function=callback_function, error_function=error_function)

    start_time = time.time()

    # Initialize a dictionary to store all timelines
    all_timelines_avg = {}

    for ligand_mz_value in ligand_mz_values:
        try:
            # Get the intensity values for the ligand curve
            timeline = parser.get_intensity_timeline(m_z=ligand_mz_value, area_range=range_ligand, function=function_ligand, use_cache=use_cache)
        except ValueError as e:
            error_function(f"{str(e)} Ligand is ignored.", "log print")
            timeline = []

        # Store the timeline in the dictionary with the m/z value as the key
        all_timelines_avg[str(ligand_mz_value)] = timeline

    callback_function(f"Time taken to get the intensity data: {time.time() - start_time:.2f} seconds.", "log")

    # Calculate the mass of the protein
    protein_mass = protein_mz_value * protein_charge_state

    if protein_charge_state_averaging_window <= 0:
        protein_mz_values = [protein_mass / protein_charge_state]
    else:
        # Create a lists of protein m/z values to scan
        protein_mz_values = [protein_mass / (protein_charge_state + i) for i in range(-protein_charge_state_averaging_window + 1,
                                                                                      protein_charge_state_averaging_window - 1)]

    # Get the protein curves and sum them up
    if len(protein_mz_values) <= 1:
        try:
            protein_curve = parser.get_intensity_timeline(m_z=protein_mz_values[0], area_range=range_protein, function=function_protein, use_cache=use_cache)
        except ValueError as e:
            error_function(str(e), "log print")
            protein_curve = []
    else:
        all_protein_curves = []
        for protein_mz_value in protein_mz_values:
            try:
                timeline = parser.get_intensity_timeline(m_z=protein_mz_value, area_range=range_protein, function=function_protein, use_cache=use_cache)
            except ValueError as e:
                error_function(f"{str(e)} Protein charge state is ignored.", "log")
                timeline = []

            all_protein_curves.append(timeline)

        protein_curve = np.sum(all_protein_curves, axis=0)

    # Assure that the length of the ligand curves is the same as the protein curve
    if len(protein_curve) != len(all_timelines_avg[str(ligand_mz_values[0])]):
        # Append zeros to the shorter curve
        if len(protein_curve) < len(all_timelines_avg[str(ligand_mz_values[0])]):
            protein_curve = np.append(protein_curve, np.zeros(len(all_timelines_avg[str(ligand_mz_values[0])]) - len(protein_curve)))
        else:
            protein_curve = protein_curve[:len(all_timelines_avg[str(ligand_mz_values[0])])]

    # Get the ligand curves in the same order as the m/z values
    ligand_curves = [np.array(all_timelines_avg[str(mz_value)]) for mz_value in ligand_mz_values]

    if start_x_axis and end_x_axis:
        # Only keep the data specified in the start and end time
        ligand_curves = [curve[start_x_axis:end_x_axis] for curve in ligand_curves]
        protein_curve = protein_curve[start_x_axis:end_x_axis]

    normalized_ligand_curves = [normalize_curve(curve) for curve in ligand_curves]
    normalized_protein_curve = normalize_curve(protein_curve)

    # Initialize the comparator class
    comparator = CurveSimilarityDetector(
        dtw_threshold=dtw_threshold,
        pearson_threshold=pearson_threshold,
        window_length=window_length,
        polyorder=polyorder,
        protein_curve=normalized_protein_curve,
        use_savgol=use_savgol
    )

    start_time = time.time()
    # Compare the ligand curves to the protein curve
    similarities = comparator.are_curves_similar_list(normalized_ligand_curves, num_processes=1, tracked_mode=True)

    callback_function(f"Time taken to compare the ligand curves: {time.time() - start_time:.2f} seconds.", "log")

    normalized_return_bin_curves = []
    normalized_return_protein_curve = []
    # Normalize based on the selected mode
    match normalization_mode:
        case 1:
            normalized_return_bin_curves = ligand_curves
            normalized_return_protein_curve = protein_curve
            pass
        case 2:
            # Normalize each ligand curve individually
            normalized_return_bin_curves = normalized_ligand_curves
            normalized_return_protein_curve = normalize_curve(protein_curve)
            pass
        case 3:
            # Normalize all ligand curves together
            # Find maximum value in all curves
            max_value = max([max(curve) for curve in ligand_curves])
            # Normalize all curves together
            normalized_return_bin_curves = [curve / max_value for curve in ligand_curves]
            normalized_return_protein_curve = normalize_curve(protein_curve)
            pass

    return ligand_mz_values, normalized_return_bin_curves, ligand_curves, similarities, normalized_return_protein_curve, parser.CreationDate

def analyze_untargeted(file_path, catalyst_manager, dtw_threshold=12, pearson_threshold=0.85,
                       window_length=5, polyorder=3, protein_mz_value=0, start_value=50, end_value=8000,
                       range_ligand=0.02, range_protein=0.02, num_processes=4, num_processes_analysis=4,
                       use_savgol=True, range_threshold=3, protein_range_threshold=4,
                       function_ligand=2, function_protein=2, use_cache=True, protein_charge_state=0, charge_state_radius=0,
                       protein_charge_state_averaging_window=1, start_x_axis=None, end_x_axis=None, callback_function=None,
                       error_function=None, normalization_mode=0):
    """
        Analyze untracked ligand curves and return filtered results.

        Args:
            file_path (str): Path to the input file.
            catalyst_manager (CATALYST_manager): Manages the CATALYST directory.
            dtw_threshold (float): Threshold for Dynamic Time Warping (DTW) distance.
            pearson_threshold (float): Threshold for Pearson correlation.
            window_length (int): Window length for smoothing.
            polyorder (int): Polynomial order for smoothing.
            protein_mz_value (float): m/z value for the protein curve.
            start_value (float): Start value of the m/z range.
            end_value (float): End value of the m/z range.
            range_ligand (float): Range for binning m/z values for ligand curves.
            range_protein (float): Range for binning m/z values for protein curve.
            num_processes (int): Number of processes to use for parallel processing.
            num_processes_analysis (int): Number of processes to use for parallel processing of the analyzer.
            use_savgol (bool): Flag to use Savitzky-Golay filter for smoothing.
            range_threshold (float): Threshold for m/z range filtering.
            protein_range_threshold (float): Threshold for protein m/z range filtering.
            function_ligand (int): Function to use for binning m/z values for ligand curves.
            function_protein (int): Function to use for binning m/z values for protein curve.
            use_cache (bool): Flag to use cache for storing the intensity values.
            protein_charge_state (int): Charge state of the protein.
            charge_state_radius (int): Radius for scanning different charge states.
            protein_charge_state_averaging_window (int): Window for averaging the protein charge state.
            start_x_axis (int): Start time which to use for the analysis
            end_x_axis (int): End time which to use for the analysis
            callback_function (function): Callback function to print text to the GUI.
            error_function (function): Callback function to print error messages to the GUI.
            normalization_mode (int): Mode for normalization. 0: No normalization, 1: All ligands are normalized individually , 2: All ligands are normalized together.
        Returns:
            list: A list of tuples containing (m/z value, ligand curve, is_similar, DTW score, Pearson score).
    """
    callback_function("Starting untargeted search.", "log print")
    ### Initialize the parser class
    parser = TextFileReader(file_path=file_path, catalyst_manager=catalyst_manager, callback_function=callback_function, error_function=error_function)

    all_timelines_avg = parser.get_all_intensity_timelines(area_range=range_ligand, num_processes=num_processes, function=function_ligand,
                                                           start_value=start_value, end_value=end_value, use_cache=use_cache)

    # Calculate the mass of the protein
    protein_mass = protein_mz_value * protein_charge_state

    # Create a lists of protein m/z values to scan
    if protein_charge_state_averaging_window <= 0:
        protein_mz_values = [protein_mass / protein_charge_state]
    else:
        protein_mz_values = [protein_mass / (protein_charge_state + i) for i in
                            range(-protein_charge_state_averaging_window + 1, protein_charge_state_averaging_window)]

    # Get the protein curves and sum them up
    if len(protein_mz_values) <= 1:
        try:
            protein_curve = parser.get_intensity_timeline(m_z=protein_mz_values[0], area_range=range_protein, function=function_protein, use_cache=use_cache)
        except ValueError as e:
            error_function(str(e), "log print")
            protein_curve = []
    else:
        all_protein_curves = []
        for mz_value in protein_mz_values:
            try:
                timeline = parser.get_intensity_timeline(m_z=mz_value, area_range=range_protein, function=function_protein, use_cache=use_cache)
            except ValueError as e:
                error_function(f"{str(e)} Protein charge state is ignored.", "log")
                timeline = []

            all_protein_curves.append(timeline)

        protein_curve = np.sum(all_protein_curves, axis=0)

    # Assure that the length of the ligand curves is the same as the protein curve
    if len(protein_curve) != len(all_timelines_avg[next(iter(all_timelines_avg.keys()))]):
        # Append zeros to the protein curve or remove the last values until it matches
        if len(protein_curve) < len(all_timelines_avg[next(iter(all_timelines_avg.keys()))]):
            protein_curve = np.append(protein_curve, np.zeros(len(all_timelines_avg[next(iter(all_timelines_avg.keys()))]) - len(protein_curve)))
        else:
            protein_curve = protein_curve[:len(all_timelines_avg[next(iter(all_timelines_avg.keys()))])]

    ### Get all values from dict between start and end value
    filtered_keys = sorted([key for key in all_timelines_avg.keys() if start_value <= float(key) < end_value], key=float)
    bin_curves = [np.array(all_timelines_avg[key]) for key in filtered_keys]

    if start_x_axis and end_x_axis:
        ### Only keep the data specified in the start and end time
        bin_curves = [curve[start_x_axis:end_x_axis] for curve in bin_curves]
        protein_curve = protein_curve[start_x_axis:end_x_axis]

    normalized_bin_curves = [normalize_curve(curve) for curve in bin_curves]
    normalized_protein_curve = normalize_curve(protein_curve)

    # Initialize the comparator class
    comparator = CurveSimilarityDetector(
        dtw_threshold=dtw_threshold,
        pearson_threshold=pearson_threshold,
        window_length=window_length,
        polyorder=polyorder,
        protein_curve=normalized_protein_curve,
        use_savgol=use_savgol
    )

    start_time = time.time()
    ### Compare the bin curves to the protein curve
    analysis_result = comparator.are_curves_similar_list(normalized_bin_curves, num_processes=num_processes_analysis)

    callback_function(f"Time taken to compare the bin curves: {time.time() - start_time:.2f} seconds.", "log")

    ### Get the mz value for the similar curves
    all_mz_values = [float(key) for key in filtered_keys]

    ### Filter similar curves based on the range threshold
    results = group_and_filter_results(all_mz_values,
                                     bin_curves,
                                     analysis_result,
                                     range_threshold,
                                     protein_range_threshold,
                                     protein_mz_value,
                                     protein_charge_state,
                                     charge_state_radius
                                    )

    if not results:
        callback_function("No similar curves found.", "log print")

    filtered_mz_values, filtered_curves, filtered_results = results

    normalized_return_bin_curves = []
    normalized_return_protein_curve = []
    # Normalize based on the selected mode
    match normalization_mode:
        case 1:
            normalized_return_bin_curves = filtered_curves
            normalized_return_protein_curve = protein_curve
            pass
        case 2:
            # Normalize each ligand curve individually
            normalized_return_bin_curves = [normalize_curve(curve) for curve in filtered_curves]
            normalized_return_protein_curve = normalize_curve(protein_curve)
            pass
        case 3:
            # Normalize all ligand curves together
            # Find maximum value in all curves
            max_value = max([max(curve) for curve in filtered_curves])
            # Normalize all curves together
            normalized_return_bin_curves = [curve / max_value for curve in filtered_curves]
            normalized_return_protein_curve = normalize_curve(protein_curve)
            pass

    return filtered_mz_values, normalized_return_bin_curves, filtered_curves, filtered_results, normalized_return_protein_curve, parser.CreationDate

