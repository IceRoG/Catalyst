import PyInstaller.__main__
import os

# Define the path to the main script
MAIN_SCRIPT = os.path.join('src', 'main.py')  # Adjusted for the src/ directory structure

# Define the path to the icon file
ICON_PATH = os.path.join('src', 'data', 'icons', 'CATALYST_logo.ico')  # Adjust this path to your icon's actual location

# PyInstaller options
PYINSTALLER_OPTIONS = [
    '--onefile',                # Create a single executable file
    '--windowed',               # No console window (for GUI applications)
    '--name=CATALYST',          # Name of the output executable
    '--icon', ICON_PATH         # Specify the icon file with correct argument structure
]

# Run PyInstaller to create the executable
PyInstaller.__main__.run([MAIN_SCRIPT] + PYINSTALLER_OPTIONS)