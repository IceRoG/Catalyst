from datetime import datetime
import os
from matplotlib.figure import Figure
from reportlab.pdfgen import canvas
from reportlab.lib import pagesizes

from src.grapher import DataGrapher
from src.settings.settings import Settings


def generate_PDF(directory : str, scan_date : str, settings: Settings, protein_curve : list[float], protein_mz : float, 
                ligand_curves : list[list[float]], ligand_mzs : list[float], ligand_similarities : list[tuple[bool, float, float]], 
                ligand_intensities : list[float], single_plot : bool = True, normalized : bool = True, x_axis : list[int] = None):
    """
        Generates a PDF in the given directory containing the given scan date and plotting the given protein/ligands.

        Parameters:
            directory           (raw string): The directory where the PDF file will be created
            scan_date           (string): The scan date which will be displayed in the file name and PDF title
            protein_curve       (list of float): Intensity values to plot for the protein
            protein_mz          (float): The m/z value of the protein
            ligand_curves       (list of lists of float): Intensity values to plot for each of the ligands
            ligand_mzs          (list of float): The m/z values of the ligands
            ligand_similarities (list of tuples (bool, float, float)): The similarity for each ligand as (Is similar?, DTW, Pearson)
            ligand_intensities  (list of float): The EIC intensities of the ligands
            single_plot         (bool): Whether protein and ligand should both be displayed in one single plot (default) or in two separate ones
            normalized          (bool): Whether intensity values are normalized
            x_axis              (list of integer or None): The x-axis (scan numbers analyzed) for the output, None meaning 0, 1, ...
    """

    # Initialize pdf
    formatted_date = scan_date.replace(" ", "_").replace(":", "-")
    file_path = os.path.join(directory, "scan_" + f"{formatted_date}" + ".pdf")
    pdf = OutputPDF(file_path, PDFMetadata(datetime.now().strftime("%b %d %H:%M %Y"), scan_date))
    pdf.setup_PDF("Catalyst Analysis results")

    # Initialize grapher and figure to plot on
    grapher = DataGrapher("Scan Number", "Intensity")

    # Add scatterplot of ligand similarities (Pearson, DTW)
    scatterplot_figure = Figure(figsize=(6, 4), dpi=100)
    scatterplot_graph = os.path.join(directory, f"scatterplot_graph" + ".png")
    grapher.save_ligand_scatterplot(ligand_similarities, ligand_intensities, scatterplot_figure, scatterplot_graph)
    pdf.add_graphic(scatterplot_graph, "Pearson-DTW ligand scatterplot")
    
    # Add bar chart of ligand EIC intensities
    bar_chart_figure = Figure(figsize=(6, 4), dpi=100)
    bar_chart_graph = os.path.join(directory, f"bar_chart_graph" + ".png")
    grapher.save_EIC_bar_chart(ligand_mzs, ligand_intensities, bar_chart_figure, bar_chart_graph)
    pdf.add_graphic(bar_chart_graph, "Ligand EIC intensities")

    if(single_plot):
        # Add graphs for comparisons between intensities for protein and ligands
        for i in range(len(ligand_curves)):
            comparison_figure = Figure(figsize=(6, 4), dpi=100)
            comparison_figure.suptitle(
                f"Pearson similarity: {round(ligand_similarities[i][2]*100,2)}%   DTW score: {round(ligand_similarities[i][1], 2)}"
                ) # Add Pearson and DTW values above graph
            comparison_graph = os.path.join(directory, f"comparison{i}_graph" + ".png")
            grapher.save_comparison_graph(x_axis, protein_curve, protein_mz, ligand_curves[i], ligand_mzs[i],
                                        comparison_figure, comparison_graph, 
                                        y_axis = [0, 1.05] if normalized else [0, 1.05 * max(max(protein_curve), max(ligand_curves[i]))])
            pdf.add_graphic(comparison_graph, f"Intensity graph comparing protein and ligand {i + 1}")
    else:
        # Save graph of intensity for protein
        protein_figure = Figure(figsize=(6, 4), dpi=100)
        protein_graph = os.path.join(directory, "protein_graph" + ".png")
        grapher.save_graph(x_axis, protein_curve, protein_figure, protein_graph, mz_value=protein_mz, 
                           y_axis = [0, 1.05] if normalized else [0, 1.05 * max(protein_curve)])
        
        # Add separate graphs of intensity for protein and ligands
        for i in range(len(ligand_curves)):
            ligand_figure = Figure(figsize=(6, 4), dpi=100)
            ligand_figure.suptitle(
                f"Pearson similarity: {round(ligand_similarities[i][2]*100,2)}%   DTW score: {round(ligand_similarities[i][1], 2)}"
                ) # Add Pearson and DTW values above graph
            ligand_graph = os.path.join(directory, f"ligand{i}_graph" + ".png")
            grapher.save_graph(x_axis, ligand_curves[i], ligand_figure, ligand_graph, 'c', ligand_mzs[i],
                               y_axis = [0, 1.05] if normalized else [0, 1.05 * max(max(protein_curve), max(ligand_curves[i]))])

            pdf.add_graphic(protein_graph, "Intensity graph for protein")
            pdf.add_graphic(ligand_graph, f"Intensity graph for ligand {i + 1}")
            
    pdf.write_settings(settings)
    pdf.write_metadata()

    # Save PDF and clean up temporary files
    pdf.save_PDF()
    grapher.delete_all_graphs()



class PDFMetadata:
    
    
    def __init__(self, creation_date : str, scan_date : str):
        self.creation_date = ("Creation Date", creation_date)
        self.analysis_date = ("Scan Date", scan_date)
        
        
    def get_metadata(self):
        return list(self.__dict__.values())



# A class for managing instances of scan result PDFs
class OutputPDF:
    # Attributes to manage graphic placement
    graphic_at_top = True
    graphics_on_page = 0
    page_number = 1
    
    def __init__(self, path : str, metadata : PDFMetadata):
        """
            Constructs PDF, sets save location to given file path.
            
            Parameters:
                path (raw string): The path where the PDF will be saved upon completion
        """
        
        page_size = pagesizes.A4
        self.width, self.height = page_size
        self.pdf = canvas.Canvas(path, pagesize= page_size)
        self.metadata = metadata

        
    def add_graphic(self, path : str, description : str):
        """
            Adds the given graphic with the given caption to the pdf in the next free available spot, creating a new page if necessary. 

            Parameters:
                path        (raw string): The path to the graphic (png/jpg/...) to be inserted 
                description (string): The caption to be inserted under the graphic
        """
        
        # Create new page if current page already has 2 graphics
        if (self.graphics_on_page >= 2): 
            self.new_page()
            
        # Compute coordinates for graphic at top/bottom of page
        graphic_y = self.height - (5/10 * self.height) if self.graphic_at_top else self.height - (9/10 * self.height)
        
        # Insert graphic and caption
        self.pdf.drawImage(path, x= 1/8 * self.width, y= graphic_y, 
                           width= 6/8 * self.width, height= 1/3 * self.height)
        self.pdf.setFont("Courier", 15)
        self.pdf.drawCentredString(x = self.width/2, y = graphic_y - 20,
                                   text= description)
        
        # Update page state
        self.graphics_on_page += 1
        self.graphic_at_top = not self.graphic_at_top
    
    
    def new_page(self):
        """
        Adds a new page to the PDF with the default design and resets the page state.
        """
        
        # Add page and update attributes
        self.pdf.showPage()
        self.page_number += 1
        self.graphics_on_page = 0
        
        self.write_page_number()
            
    
    def save_PDF(self):
        """
        Saves the PDF to the path specified upon creation.
        """
        
        self.pdf.save()
      
        
    def setup_PDF(self, title : str):
        """
            Designs the first page of the PDF with the default design.

            Parameters:
                title (string): The title of the document to be inserted at the top
        """
        
        # Write title
        self.pdf.setFont("Helvetica", 30)
        self.pdf.drawCentredString(x = self.width/2, y = self.height - 80, text= title)
        
        self.write_page_number()
        
        
    def write_page_number(self):
        """
        Write the current page number in the bottom right corner of the page.
        """
        
        self.pdf.setFont("Times-Roman", 13)
        self.pdf.drawRightString(x = 95/100 * self.width, y = 10, text = str(self.page_number))
        

    def write_settings(self, settings : Settings):
        """
            Writes the given settings onto two pages: second page for advanced settings, first for all the rest.

        Args:
            settings (Settings): The settings object to be written
        """
        
        # First page of settings
        self.new_page()
        y = self.height - 50 # Current writing height
        
        # General settings
        self.pdf.setFont("Helvetica", 17)
        self.pdf.drawCentredString(x = self.width/2, y = y, text = "General Settings")
        y -= 40
        _, general_settings = settings.general_settings.get_settings()
        self.pdf.setFont("Courier", 13)
        for setting in general_settings:
            text = setting.print_setting()
            while(len(text) > 65):
                self.pdf.drawString(x = 30, y = y, text = text[:65])
                text = text[65:]
                y -= 15
            self.pdf.drawString(x = 30, y = y, text = text)
            y -= 20
        y -= 40

        if settings.general_settings.analysis_mode.value == "Targeted":
            # Targeted settings
            self.pdf.setFont("Helvetica", 17)
            self.pdf.drawCentredString(x = self.width/2, y = y, text = "Targeted Settings")
            y -= 40
            _, targeted_settings = settings.targeted_settings.get_settings()
            self.pdf.setFont("Courier", 13)
            for setting in targeted_settings:
                text = setting.print_setting()
                while(len(text) > 65):
                    self.pdf.drawString(x = 30, y = y, text = text[:65])
                    text = text[65:]
                    y -= 15
                self.pdf.drawString(x = 30, y = y, text = text)
                y -= 20
            y -= 40

        elif settings.general_settings.analysis_mode.value == "Untargeted":
            # Untargeted settings
            self.pdf.setFont("Helvetica", 17)
            self.pdf.drawCentredString(x = self.width/2, y = y, text = "Untargeted Settings")
            y -= 40
            _, advanced_settings = settings.untargeted_settings.get_settings()
            self.pdf.setFont("Courier", 13)
            for setting in advanced_settings:
                text = setting.print_setting()
                while(len(text) > 65):
                    self.pdf.drawString(x = 30, y = y, text = text[:65])
                    text = text[65:]
                    y -= 15
                self.pdf.drawString(x = 30, y = y, text = text)
                y -= 20
            y -= 40
        
        # Output settings
        self.pdf.setFont("Helvetica", 17)
        self.pdf.drawCentredString(x = self.width/2, y = y, text = "Output Settings")
        y -= 40
        _, advanced_settings = settings.output_settings.get_settings()
        self.pdf.setFont("Courier", 13)
        for setting in advanced_settings:
            text = setting.print_setting()
            while(len(text) > 65):
                self.pdf.drawString(x = 30, y = y, text = text[:65])
                text = text[65:]
                y -= 15
            self.pdf.drawString(x = 30, y = y, text = text)
            y -= 20
            
        # Second page of settings
        self.new_page()
        y = self.height - 50
        
        # Advanced settings
        self.pdf.setFont("Helvetica", 17)
        self.pdf.drawCentredString(x = self.width/2, y = y, text = "Advanced Settings")
        y -= 40
        _, advanced_settings = settings.advanced_settings.get_settings()
        self.pdf.setFont("Courier", 13)
        for setting in advanced_settings:
            text = setting.print_setting()
            while(len(text) > 65):
                self.pdf.drawString(x = 30, y = y, text = text[:65])
                text = text[65:]
                y -= 15
            self.pdf.drawString(x = 30, y = y, text = text)
            y -= 20
           
            
    def write_metadata(self):
        """
            Writes the given settings onto two pages: second page for advanced settings, first for all the rest.

        Args:
            settings (Settings): The settings object to be written
        """
        
        self.new_page()
        y = self.height - 50 # Current writing height
        
        self.pdf.setFont("Helvetica", 17)
        self.pdf.drawCentredString(x = self.width/2, y = y, text = "Metadata")
        y -= 40
        
        self.pdf.setFont("Courier", 13)
        for entry in self.metadata.get_metadata():
            self.pdf.drawString(x = 30, y = y, text = f"{entry[0]} = {entry[1]}")
            y -= 20