import os

from matplotlib.figure import Figure

class GraphingError(ValueError):
    pass

# Class for methods to convert data to graphs
class DataGrapher:

    def __init__(self, x_axis_name : str = None, y_axis_name : str = None):
        """
            Constructs the grapher for graphs with the given axis labels. 

            Parameters:
                x_axis_name (string): The label for the x-axis of the graphs (optional)
                y_axis_name (string): The label for the y-axis of the graphs (optional)
        """

        self.x_axis_name = x_axis_name
        self.y_axis_name = y_axis_name
        self.files = [] # Array with paths of all saved graphs


    def set_x_axis(self, x_axis_name : str):
        """
            Sets the given label to the x-axis.

            Parameters:
                x_axis_name (string): The label for the x-axis of the graphs
        """

        self.x_axis_name = x_axis_name


    def set_y_axis(self, y_axis_name : str):
        """
            Sets the given label to the y-axis.

            Parameters:
                y_axis_name (string): The label for the y-axis of the graphs
        """

        self.y_axis_name = y_axis_name


    def plot_graph(self, x_values : list[float], y_values : list[float], figure : Figure, subplot : int = 111, 
                   color : str = 'r', mz_value : float = None, y_axis : list[float] = [0, 1.05]):
        """
            Plots the graph of the given x and y-values onto the given figure.

            Parameters:
                x_values (list of float or None): The series of x-values to be plotted, None meaning default [0, 1, ...].
                y_values (list of float): The y-values to be plotted. (Amount and lengths of corresponding x- and y- values should be equal)
                figure   (matplotlib figure): The figure where the graph will be plotted on for further usage
                subplot  (integer): The subplot inside the figure (see matplotlib documentation)
                color    ('char'): The color for the first plot ('r' = red, 'c' = cyan, ... - see matplotlib colors)
                mz_value (float): The m/z value for the curve (if applicable)
                y_axis   (list of float): The two float values used as start and end for the y_axis, default = [0, 1.05]
        """
        
        self.plot_graphs(None if x_values is None else [x_values], 
                         [y_values], 
                         figure, 
                         subplot, 
                         [color], 
                         None if mz_value is None else [mz_value],
                         None if mz_value is None else f"m/z: {mz_value}",
                         y_axis
                         )
        
        
    def plot_graphs(self, x_values_list : list[list[float]], y_values_list : list[list[float]], figure : Figure, subplot : int = 111, 
                    color_list : list[str] = None, mz_value_list : list[float] = None, title : str = None, y_axis : list[float] = [0, 1.05]):
        """
            Plots the graphs using the given x and y-values onto the given figure. 

            Parameters:
                x_values_list (list of list of float): The series of x-values to be plotted, None meaning default [0, 1, ...].
                y_values_list (list of list of float): The series of y-values to be plotted. (Amount and lengths of corresponding x- and y- values should be equal)
                figure        (matplotlib figure): The figure where the graph will be plotted on for further usage
                subplot       (integer): The subplot inside the figure (see matplotlib documentation)
                color_list    (list of char): The colors for the individual plots ('r' = red, 'c' = cyan, ... - see matplotlib colors); None => default
                m_z_list      (list of float): The m/z values for the plot labels; None => no labels
                title         (string): The title of the plot to display, None => no title
                y_axis        (list of float): The two float values used as start and end for the y_axis, default = [0, 1.05]
        """
        
        if(not x_values_list is None):
            if(len(x_values_list) != len(y_values_list)):
                raise GraphingError(f"Received {len(x_values_list)} series of x-values, but {len(y_values_list)} series of y-values; These amounts must be equal")
            for i in range(len(x_values_list)):
                if(len(x_values_list[i]) != len(y_values_list[i])):
                    raise GraphingError(f"Received {len(x_values_list[i])} x-values, but {len(y_values_list[i])} y-values; These amounts must be equal")
        
        if(subplot < 111 or subplot > 999 or (subplot % 10) > ((subplot //10 % 10) * (subplot //100))):
            raise GraphingError(f"Subplot parameter {subplot} invalid - refer to matplotlib documentation")      
        
        if(len(y_axis) != 2):
            raise GraphingError(f"Y-axis parameter should contain only start and end values, but it contains {len(y_axis)} values")
        
        # Specify part of figure to plot onto (subplot)
        plot = figure.add_subplot(subplot)
        
        # Set axis labels
        plot.set_xlabel(self.x_axis_name)
        plot.set_ylabel(self.y_axis_name)
        
        # Set y-axis limits
        plot.set_ylim(y_axis)
        
        # Enable grid for the visualization
        plot.grid(True)
        
        # Iterate over given sets of x and y-values
        for i in range(len(y_values_list)):
        
            # TODO: add step for range based on functions
            
            # Extract x and y values for current iteration
            x_values = range(len(y_values_list[0])) if x_values_list is None else x_values_list[i]
            y_values = y_values_list[i]
            
            # Plot values
            if not color_list is None:
                plot.plot(x_values, y_values, color = color_list[i], label= "" if mz_value_list is None else f"{mz_value_list[i]}")
            else:
                plot.plot(x_values, y_values, label="" if mz_value_list is None else f"{mz_value_list[i]}")
                
        # Add a legend for clarity
        plot.legend(loc='upper left', bbox_to_anchor=(0, 1), ncol=len(y_values_list))        
                
        # Add the title if given
        if not title is None: plot.set_title(title)


    def save_comparison_graph(self, x_values : list[float], protein_curve : list[float], protein_mz : float, ligand_curve : list[float], ligand_mz : float, 
                              figure : Figure, path : str, protein_color : str = 'r', ligand_color : str = 'b', y_axis : list[float] = [0, 1.05]):
        """
            Saves the comparison graph between the given protein and ligand to the given path.

            Parameters:
                x_values      (list of float): The x-values to be plotted, None meaning default [0, 1, ...].
                protein_curve (list of float): The y-values to be plotted for the protein. (Amount and lengths of corresponding x- and y- values should be equal)
                protein_mz    (float): The m/z value for the protein curve
                ligand_curve  (list of float): The y-values to be plotted for the ligand. (Amount and lengths of corresponding x- and y- values should be equal)#
                ligand_mz     (float): The m/z values for the ligand curve
                figure        (matplotlib figure): The figure where the graph will be plotted on for further usage
                path          (raw string): The path where the graph image will be saved upon completion
                protein_color ('char'): The color for the protein plot ('r' = red, 'c' = cyan, ... - see matplotlib colors)
                ligand_color  ('char'): The color for the ligand plot ('r' = red, 'c' = cyan, ... - see matplotlib colors)
                y_axis        (list of float): The two float values used as start and end for the y_axis, default = [0, 1.05]
        """

        self.save_graphs(
            None if x_values is None else [x_values, x_values],
            [protein_curve, ligand_curve],
            figure,
            path,
            [protein_color, ligand_color],
            [protein_mz, ligand_mz],
            f"Protein: {protein_mz} m/z   Ligand: {ligand_mz} m/z",
            y_axis
        )


    def save_graph(self, x_values : list[float], y_values : list[float], 
                   figure : Figure, path : str, color : str = 'r', mz_value : float = None, title : str = None, y_axis : list[float] = [0, 1.05]):
        """
            Saves the graphs using the given x and y-values to the given path.

            Parameters:
                x_values (list of float): The series of x-values to be plotted, None meaning default [0, 1, ...].
                y_values (list of float): The series of y-values to be plotted. (Amount and lengths of corresponding x- and y- values should be equal)
                figure   (matplotlib figure): The figure where the graph will be plotted on for further usage
                path     (raw string): The path where the graph image will be saved upon completion
                color    (char): The color for the first plot ('r' = red, 'c' = cyan, ... - see matplotlib colors)
                mz_value (float): The m/z value for the curve (if applicable)
                title    (string): The title of the plot to display, None => no title
                y_axis   (list of float): The two float values used as start and end for the y_axis, default = [0, 1.05]
        """

        self.save_graphs(None if x_values is None else [x_values], [y_values], figure, path, [color], None if mz_value is None else [mz_value], title, y_axis)


    def save_graphs(self, x_values_list : list[list[float]], y_values_list : list[list[float]], figure : Figure, 
                    path : str, color_list : list[str] = None, mz_value_list : list[float] = None, title : list[str] = None, y_axis : list[float] = [0, 1.05]):
        """
            Saves the graphs using the given x and y-values to the given path.

            Parameters:
                x_values_list (list of list of float): The series of x-values to be plotted, None meaning default [0, 1, ...].
                y_values_list (list of list of float): The series of y-values to be plotted. (Amount and lengths of corresponding x- and y- values should be equal)
                figure        (matplotlib figure): The figure where the graph will be plotted on for further usage
                path          (raw string): The path where the graph image will be saved upon completion
                color_list    (list of char): The colors for the individual plots ('r' = red, 'c' = cyan, ... - see matplotlib colors); None => default
                m_z_list      (list of float): The m/z values for the plot labels; None => no labels
                title         (string): The title of the plot to display, None => no title
                y_axis        (list of float): The two float values used as start and end for the y_axis, default = [0, 1.05]
        """
        if(not os.path.exists(os.path.dirname(path))): raise GraphingError(f"Folder to save in: {path} does not exist")

        # Plot graph
        self.plot_graphs(x_values_list, y_values_list, figure, 111, color_list, mz_value_list, title, y_axis)

        # Save graph as image
        figure.savefig(path, bbox_inches='tight') # 'tight' ensures that no part of figure is cut off in image
        self.files.append(path)


    def delete_all_graphs(self):
        """
            Deletes all saved graphs.
        """

        for file in self.files:
            os.remove(file)
        self.files = []