# Chromatography-Assisted Time Alignment for Ligand Yield and Screening Tool

## Overview
This project aims to develop an automated data analysis tool for mass spectrometry, specifically designed to identify noncovalent interactions between proteins and ligands. By leveraging gentle separation techniques in mass spectrometry, this tool will help screen multiple ligand candidates in complex mixtures, automating a process traditionally done manually and thus highly time-consuming.

The tool will process mass spectrometry data to distinguish bound molecules from non-binders, enhancing the efficiency of analyzing large datasets while maintaining high accuracy.

## Project Goals
- **Automate Mass Spectrometry Data Analysis**: Streamline the identification of molecular interactions in mass spectrometry data through automation.
- **Detection of Noncovalent Binding**: Identify non-permanent binding interactions between proteins and small molecule ligands.
- **Curve and Signal Processing**: Analyze and generate curves representing protein and ligand traces, with calculations of mass-to-charge ratios for ligand identification.
- **Noise Reduction and Signal Enhancement**: Implement methods to handle signal-to-noise challenges in real-world data.

## Features
- **Protein-Ligand Interaction Identification**: Identifies bound molecules based on mass spectrometry data.
- **Statistical Approaches**: Applies statistical testing for classifying signals as bound or unbound ligands.
- **Curve Visualization**: Outputs graphical representations of protein and ligand curves, with mass/charge data, into a PDF report.
- **High-Throughput Screening**: Capable of handling large datasets with multiple ligand candidates, reducing manual effort.

## Usage
1. **Input Data**: The tool accepts mass spectrometry data files with (mass vs. intensity) data arrays.
2. **Processing**: The data is analyzed to extract intensity vs. time traces for specific masses, then filtered for noise and classified as bound or unbound.
3. **Output**: Generates a PDF report with:
   - Curve plots for both protein and ligand
   - Calculations of mass/charge (m/z) values for detected ligands

## Dependencies
- **Load Dependencies**:
  ```bash
  pip install -r requirements.txt
  ```
- **Update Dependencies**: \
  Ensure your terminal is in the same directory as requirements.txt and that a virtual environment (venv) is activated before running this command.
  ```bash
  python -c "import subprocess; subprocess.run('pip freeze', stdout=open('requirements.txt', 'w', encoding='utf-8'))"
  ```

## Compile to .exe
- **Run in terminal**:
  ```bash
  python setup.py install
  python build.py
    ```
- The executable file will be generated in the **dist** folder.

- You can also download a compiled version of the software as an .exe file under this link.
https://1drv.ms/u/c/fc611cd214a4ebd4/EbX4Tc5rY4NPnvEcMM6Ztv0Bi3vRNqwXkbTDBClnE6UUNQ?e=TG7w50

## Disclaimer
This software was developed by students at TU Darmstadt as part of a Bachelorpraktikum. While we strive to ensure its functionality and accuracy, it is provided as-is with only minimal support and updates.

We still greatly appreciate any feedback or feature requests, which can be shared via [your preferred contact method, e.g., GitHub Issues or email]. However, please note that future maintenance and improvements will be limited.
