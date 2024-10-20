import os
import sys


def find_and_add_lilbro_utils():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for root, dirs, files in os.walk(current_dir):
        if "lilbro_utils" in dirs:
            sys.path.append(root)
            return


# Find and add lilbro_utils to sys.path
find_and_add_lilbro_utils()
