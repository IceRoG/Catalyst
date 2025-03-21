class Setting:

    def __init__(self, name: str, print_name: str, value, data_type):
        self.name = name
        self.print_name = print_name
        self.value = value
        self.data_type = data_type
        
    def print_setting(self):
        return f"{self.print_name} = {self.value}"