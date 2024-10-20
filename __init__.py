import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
for root, dirs, files in os.walk(current_dir):
    if "lilbro_utils" in dirs:
        sys.path.append(root)
