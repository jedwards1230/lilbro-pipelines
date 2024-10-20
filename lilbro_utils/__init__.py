import os
import importlib

# Get the directory of the current file
current_dir = os.path.dirname(__file__)

# List all Python files in the current directory
for filename in os.listdir(current_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]  # Remove the .py extension
        importlib.import_module(f".{module_name}", package=__name__)
