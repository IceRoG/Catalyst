import csv
import os


def generateGeneralCSV(directory : str, date : str, 
                       ligand_mzs : list[float], ligand_similarities : list[tuple[bool, float, float]], ligand_intensities : list[float]):
    """
        Generates a CSV file in the given directory named after the given scan date containing central information about each ligand in the analysis.
        (Ligand information: identifier, m/z value, Pearson similarity, DTW score, EIC intensity)

        Parameters:
            directory           (raw string): The directory where the CSV file will be created
            date                (string): The scan date which will be displayed in the file name
            ligand_mzs          (list of float): The m/z values of the ligands
            ligand_similarities (list of tuples (bool, float, float)): The similarity for each ligand as (Is similar?, DTW, Pearson)
            ligand_intensities  (list of float): The EIC intensities of the ligands
    """
    
    # Compute file path with directory and scan date
    file_path = os.path.join(directory, 
                             "scan_" + f"{date}_" + "all_ligands" + ".csv" )
    
    # Initialize CSV file to write in
    with open(file_path, 'w', newline='') as csv_file:
        
        # Set up columns
        columns = ["Ligand Number", "m/z", "Pearson similarity", "DTW score", "EIC intensity"]
        writer = csv.DictWriter(csv_file, fieldnames = columns)
        writer.writeheader()
        
        # Write information of each ligand
        for i in range(len(ligand_mzs)):
            writer.writerow(
                {"Ligand Number": i + 1, 
                 "m/z": ligand_mzs[i],
                 "Pearson similarity": round(ligand_similarities[i][2]*100, 2), # Convert to percentage
                 "DTW score": round(ligand_similarities[i][1], 2),
                 "EIC intensity": round(ligand_intensities[i], 2)
                 })


def generateIntensitiesCSV(directory : str, date : str, ligand_number : int, intensity_values : list[float], mass_over_charge : float = None, start_scan : int = 0):
    """
        Generates a CSV file in the given directory named after the given scan date and ligand number, 
        containing the intensity values and their scan numbers. 

        Parameters:
            directory        (raw string): The directory where the CSV file will be created
            date             (string): The scan date which will be displayed in the file name
            ligand_number    (integer): The ordinal number of the ligand (0 = protein, then 1 = first ligand, ...)
            intensity_values (list of floats): Intensity values to write in the CSV file
            mass_over_charge (float): Mass over charge value to write in the CSV file name, None => ignored
            start_scan       (integer): First scan that was used in analysis (default 0)
    """
    
    # Compute file path with directory and file information
    file_path = os.path.join(directory, 
                             "scan_" + f"{date}_" + ("protein" if ligand_number == 0 else f"ligand{ligand_number}") 
                             + ("" if mass_over_charge is None else f"_mz_{mass_over_charge:.2f}") + ".csv" )
    
    # Initialize CSV file to write in
    with open(file_path, 'w', newline='') as csv_file:
        
        # Set up columns
        columns = ["Scan Number", "Intensity"]
        writer = csv.DictWriter(csv_file, fieldnames= columns)
        writer.writeheader()
        
        # Write intensity values
        for i in range(len(intensity_values)):
            writer.writerow({"Scan Number": start_scan + i, "Intensity": intensity_values[i]})