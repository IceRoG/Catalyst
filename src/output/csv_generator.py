import csv
import os

def generateCSV(directory : str, date : str, ligand_number : int, intensity_values : list[float], mass_over_charge : float = None, start_scan : int = 0):
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