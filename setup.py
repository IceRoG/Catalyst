from setuptools import setup, find_packages
import os

# Read the requirements from requirements.txt
with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

setup(
    name="CATALYST",
    version="1.0.0",
    description="Analyze mass spectrometry data to identify ligands bonded with a protein.",
    author="Bachelorpraktikum Gruppe 10",
    author_email="bp.gruppe10@proton.me",
    packages=find_packages('src'),  # Automatically find packages in src/ if any
    package_dir={'': 'src'},        # Tell setuptools to look for packages in src/
    install_requires=install_requires,
)
