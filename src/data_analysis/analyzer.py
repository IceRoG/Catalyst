from concurrent.futures import ProcessPoolExecutor
from itertools import groupby
import numpy as np
from fastdtw import fastdtw
from scipy.signal import savgol_filter
from multiprocessing import cpu_count

def get_list_from_mz_and_charge(mz_value=0, charge_state=0, radius=3):
    """
    Get a list of m/z values for a given m/z value and charge state.
    :param mz_value: m/z value of the protein curve.
    :param charge_state: Charge state of the protein curve.
    :param radius: Number of charge states to consider.
    :return: List of m/z values.
    """
    if radius <= 0:
        return [mz_value]
    return [mz_value * charge_state / i for i in range(charge_state-radius, charge_state+radius+1) if i > 0]

def group_and_filter_results(mz_values, curves, results, range_threshold=3, protein_range_threshold=4,
                             protein_mz_value=0, protein_charge_state=0, charge_state_radius=4):
    """
    Groups similar m/z values by a range and keeps one representative from each group.
    :param mz_values: List of m/z values corresponding to the curves.
    :param curves: List of curves that were compared.
    :param results: List of (is_similar, dtw_distance, pearson_corr) for each curve.
    :param range_threshold: Maximum difference between m/z values to group them.
    :param protein_range_threshold: Maximum difference between protein m/z value and other m/z values to ignore them.
    :param protein_mz_value: m/z value of the protein curve.
    :param protein_charge_state: Charge state of the protein curve.
    :param charge_state_radius: Number of charge states to consider.
    :return: Filtered lists of m/z values, curves, and results.
    """
    mz_protein_charges = get_list_from_mz_and_charge(protein_mz_value, protein_charge_state, charge_state_radius)

    # Filter out invalid results (e.g., NoneType values or values that are the protein mass value)
    valid_data = [
        (mz, curve, result)
        for mz, curve, result in zip(mz_values, curves, results)
        if result[1] is not None and result[2] is not None
           and not any(mz_protein_charge - protein_range_threshold <= mz <= mz_protein_charge + protein_range_threshold
                       for mz_protein_charge in mz_protein_charges)
    ]

    # Sort by m/z values
    sorted_data = sorted(valid_data, key=lambda x: x[0])
    grouped_data = []

    if range_threshold <= 0:
        return mz_values, curves, results

    # Group sorted data by dividing each m/z value by the range threshold and rounding the result.
    # This effectively clusters m/z values that fall within the same `range_threshold` into a single group.
    # Example:
    #   If range_threshold = 3 and sorted m/z values are [2.5, 3.1, 6.8, 7.2],
    #   the groups would be:
    #       Group 1: [2.5, 3.1]  (both round to 1 after division by 3)
    #       Group 2: [6.8, 7.2]  (both round to 2 after division by 3)
    #
    # Within each group:
    #   - Select the "best" curve as the representative based on the following criteria:
    #       1. Highest Pearson correlation (indicating better similarity).
    #       2. Lowest DTW distance (used as a tiebreaker for curves with the same Pearson correlation).
    #   - This ensures that the representative curve is the most similar or relevant among the group.
    for _, group in groupby(sorted_data, key=lambda x: round(x[0] / range_threshold)):
        group = list(group)
        # Keep the curve with the best similarity metrics (e.g., highest Pearson correlation or lowest DTW)
        best_curve = max(group, key=lambda x: (x[2][2], -x[2][1]))  # Prefer high Pearson, low DTW
        # TODO: Talk about what the actual best curve from the group is
        grouped_data.append(best_curve)

    if not grouped_data:
        return None

    # Unzip filtered results
    filtered_mz_values, filtered_curves, filtered_results = zip(*grouped_data)
    return list(filtered_mz_values), list(filtered_curves), list(filtered_results)

def _calculate_dtw(curve_a, curve_b):
    """Calculate approximate Dynamic Time Warping (DTW) distance between two curves using fastdtw."""
    # Adjust curves to have zero mean (remove vertical shifts)
    mean_a = np.mean(curve_a)
    mean_b = np.mean(curve_b)
    adjusted_a = curve_a - mean_a
    adjusted_b = curve_b - mean_b

    # Convert curves to tuples of (index, value) format for fastdtw
    curve_a_tuples = list(enumerate(adjusted_a))
    curve_b_tuples = list(enumerate(adjusted_b))

    # Calculate approximate DTW distance
    distance, _ = fastdtw(curve_a_tuples, curve_b_tuples)

    return distance

def _calculate_pearson_similarity(curve_a, curve_b):
    """Calculate Pearson correlation coefficient between two curves."""
    mean_a, mean_b = np.mean(curve_a), np.mean(curve_b)
    numerator = np.sum((curve_a - mean_a) * (curve_b - mean_b))
    denominator = np.sqrt(np.sum((curve_a - mean_a) ** 2) * np.sum((curve_b - mean_b) ** 2))

    # Avoid division by zero in edge cases
    if denominator == 0:
        return 0
    return numerator / denominator

def _smooth_curve(curve, window_length=5, polyorder=3, use_savgol=True):
    """Apply Savitzky-Golay filter to smooth the intensity curve."""
    if use_savgol:
        return savgol_filter(curve, window_length=window_length, polyorder=polyorder)
    else:
        return np.convolve(curve, np.ones(2) / 2, mode='same')

def are_curves_similar(curve_a, curve_b, dtw_threshold=10, pearson_threshold=0.85):
    """
    Check if two curves are similar based on DTW and Pearson thresholds after smoothing.
    :param curve_a: First curve as a 1D numpy array.
    :param curve_b: Second curve as a 1D numpy array.
    :param dtw_threshold: DTW distance threshold for curves to be considered similar.
    :param pearson_threshold: Pearson correlation threshold for curves to be considered similar.
    :return: Tuple (Boolean indicating whether the curves are similar, DTW distance, Pearson correlation).
    """
    try:
        # Smooth the curves using Savitzky-Golay filter
        smoothed_a = _smooth_curve(curve_a)
        smoothed_b = _smooth_curve(curve_b)

        # Calculate DTW and Pearson values on the smoothed curves
        dtw_distance = _calculate_dtw(smoothed_a, smoothed_b)
        pearson_corr = _calculate_pearson_similarity(smoothed_a, smoothed_b)
        is_similar = dtw_distance < dtw_threshold and pearson_corr > pearson_threshold
        return is_similar, dtw_distance, pearson_corr
    except Exception as e:
        # TODO: Error checking and handling for multiple kinds of errors
        print(f"An error occurred while comparing curves: {e}")
        return False, None, None

def normalize_curve(curve):
    """Normalize the curve to have zero mean and unit variance."""
    if np.std(curve) == 0:
        return curve
    return curve / np.max(curve)

class CurveSimilarityDetector:
    def __init__(self, protein_curve, dtw_threshold=50, pearson_threshold=0.80, window_length=5, polyorder=3, use_savgol=True):
        """
        Initialize the similarity detector with DTW and Pearson thresholds, and Savitzky-Golay filter parameters.
        :param dtw_threshold: Maximum DTW distance for curves to be considered similar.
        :param pearson_threshold: Minimum Pearson correlation for curves to be considered similar.
        :param window_length: Window length for Savitzky-Golay filter (odd integer).
        :param polyorder: Polynomial order for Savitzky-Golay filter (less than window_length).
        :param protein_curve: Reference protein curve to compare other curves to.
        """
        self.window_length = window_length
        self.dtw_threshold = dtw_threshold
        self.pearson_threshold = pearson_threshold
        self.polyorder = polyorder
        self.protein_curve = _smooth_curve(protein_curve.flatten(), self.window_length, self.polyorder)
        self.use_savgol = use_savgol

    def are_curves_similar_list(self, curve_list, num_processes=4, tracked_mode=False):
        """
        Check if a curve is similar to any curve in a list based on DTW and Pearson thresholds after smoothing.
        :param num_processes: Number of processes to use for parallel processing.
        :param curve_list: List of curves as 1D numpy arrays.
        :param tracked_mode: Flag to indicate if the tracked mode is used.
        :return: List of tuples (Boolean indicating whether the curves are similar, DTW distance, Pearson correlation).
        """
        if self.protein_curve is None:
            raise ValueError("Protein curve not set for similarity comparison. "
                             "Please set a reference curve when instantiating the class.")
        num_processes = min(num_processes, cpu_count() - 1)  # Limit to available CPU cores
        # If the list is small, use a simple loop
        if len(curve_list) < 100 or num_processes == 1:
            return [self._is_curve_similar_to_protein_curve(curve_b, tracked_mode) for curve_b in curve_list]

        # Use parallel processing for larger lists
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            results = list(
                executor.map(self._is_curve_similar_to_protein_curve, curve_list, chunksize=20))
        return results

    def _is_curve_similar_to_protein_curve(self, curve_b, tracked_mode=False):
        """
        Check if two curves are similar based on DTW and Pearson thresholds after smoothing.
        :param curve_b: Second curve as a 1D numpy array.
        :return: Tuple (Boolean indicating whether the curves are similar, DTW distance, Pearson correlation).
        """
        try:
            # Smooth the curves using Savitzky-Golay filter
            smoothed_b = _smooth_curve(curve_b, self.window_length, self.polyorder, self.use_savgol)

            pearson_corr = _calculate_pearson_similarity(self.protein_curve, smoothed_b)
            pearson_similar = pearson_corr >= self.pearson_threshold
            if not pearson_similar and not tracked_mode:
                return False, None, pearson_corr

            # Calculate DTW and Pearson values on the smoothed curves
            dtw_distance = _calculate_dtw(self.protein_curve, smoothed_b)
            is_similar = dtw_distance < self.dtw_threshold and pearson_similar

            return is_similar, dtw_distance, pearson_corr
        except Exception as e:
            # TODO: Error checking and handling for multiple kinds of errors
            print(f"An error occurred while comparing curves: {e}")
            return False, None, None