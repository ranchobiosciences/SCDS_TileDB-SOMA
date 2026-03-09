#!/usr/bin/env python3
"""
compare_columns.py

This script compares the `obs` columns from a supplied annotated AnnData (.h5ad) file against 
the standard list of columns provided in file batch17_universal_obs_columns.txt. 
It prints out column differences and writes the observed columns from the provided dataset 
into a text file for record-keeping and stored at /SCDS_TileDB-SOMA/anndata_columns_archive. 

Usage:
    python compare_columns.py h5ad_file_path

Arguments:    
    h5ad_file_path: Path to the h5ad file to be compared.

Example:
    python compare_columns.py /wip/scds/delivery-zips/batch14/GSE137429/deliverables_2025-05-16/Ganan-Gomez_2022_Nat_Med-GSE137429-anndata-annotated.h5ad

Output:
    - Indicates if obs columns match or differ, identifying missing or new columns.
    - Writes a text file with columns from the compared dataset for record-keeping.

Author: Sinu Paul
Created: 2026-02-05
"""

import argparse
from pathlib import Path
import scanpy as sc
import json
from copy import deepcopy


def Compare_obs_columns(h5ad_file_path: Path):
    """
    Compares the `obs` columns from supplied annotated AnnData (.h5ad) file against 
    the standard list of columns provided in file batch17_universal_obs_columns.txt.

    The function:
        - Reads the current dataset's `obs` columns from the input .h5ad file.
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

def main():
    parser = argparse.ArgumentParser(description="Compare obs columns of one anndata object (from a .h5ad file) with a standard list of columns.")
    parser.add_argument(
        "h5ad_file_path", 
        type=Path, 
        help="Path to the dataset annotated.h5ad file for which the columns needs to be compared."
    )
    args = parser.parse_args()
    h5ad_file_path = args.h5ad_file_path

    print(f"Dataset .h5ad file to be checked: {h5ad_file_path}")

    if not h5ad_file_path.exists():
        raise FileNotFoundError(f"Given dataset annotated.h5ad file not found: {h5ad_file_path}")

    
    Compare_obs_columns(h5ad_file_path)


if __name__ == "__main__":
    main()