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
import scanpy as sc

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

def compare_obs_columns(h5ad_file_path: Path):
    """
    Compares the `obs` columns from supplied annotated AnnData (.h5ad) file against 
    the standard list of columns provided in file batch17_universal_obs_columns.txt.

    The function:
        - Reads the dataset's `obs` columns from the input .h5ad file.
        - Compares against the standard list of columns from the reference file.
        - Prints whether the columns match exactly or details the differences:
            - Columns absent in the current dataset with respect to standard set.
            - Columns new in the current dataset with respect to standard set.
        - Writes a text file with the `obs` columns of the current dataset for record-keeping.

    Parameters
    ----------
    h5ad_file_path : pathlib.Path
        Path to the .h5ad file to be compared.

    Returns
    -------
    None
        Prints comparison results and writes current `obs` columns to text file.
    """

    standard_columns_file_path = Path(__file__).parent / "batch17_universal_obs_columns.txt"

    with open(standard_columns_file_path, "r") as f:
        std_columns = [line.strip() for line in f if line.strip() != '']
    
    print('Number of standard columns = ', len(std_columns))

    adata = sc.read_h5ad(h5ad_file_path)
    adata_columns = list(adata.obs.columns)

    if set(std_columns) == set(adata_columns):
        print("Columns match.")
    else:
        print("Columns differ!")

        columns_absent = list(set(std_columns) - set(adata_columns))
        columns_new = list(set(adata_columns) - set(std_columns))
        if len(columns_absent) > 0:
            print("Columns absent in dataset with respect to the standard list:")
            for i in range(len(columns_absent)):
                print(str(i+1)+'. '+ columns_absent[i])
        if len(columns_new) > 0:
            print("Columns new in dataset with respect to the standard list:")
            for i in range(len(columns_new)):
                print(str(i+1)+'. '+ columns_new[i])