#!/usr/bin/env python3


"""

utils.py

This contains reusable utility functions for scripts for TileDB-SOMA objects.

Example:
    from utils import next_available_path
    path = next_available_path("output/tiledbsoma_expt")

    OR 

    import utils
    path = utils.next_available_path("output/tiledbsoma_expt")

Author: Sinu Paul
Created: 2026-02-05

"""


from pathlib import Path

def next_available_dir(path: Path) -> Path:
    """
    Returns the next available directory path by appending an incrementing number as suffix if the given path exists.
    This function will check if the given directory (e.g., tiledbsoma_expt) already exists, and will return tiledbsoma_expt_2 (1 is skipped deliberately)

    Parameters
    ----------
    path : Path
        The base directory path to check.

    Returns
    -------
    Path
        The new available directory path.
    """
    path = Path(path)
    if not path.exists():
        return path
    
    i = 2
    while True:
        new_path = Path(f"{path}_{i}")
        if not new_path.exists():
            print(f" - {path} already exists. The TileDB-SOMA experiment will be created at {new_path}")
            return new_path
        i += 1
