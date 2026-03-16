#!/usr/bin/env python3

"""
anndata_compare_columns.py

This script compares the `obs` columns from a supplied annotated AnnData (.h5ad) file against 
the standard list of columns provided in file batch17_universal_obs_columns.txt. 
It prints out column differences. 

Usage:
    python anndata_compare_columns.py h5ad_file_path

Arguments:    
    h5ad_file_path: Path to the h5ad file to be compared.

Examples:
    python anndata_compare_columns.py /wip/scds/delivery-zips/batch14/GSE137429/deliverables_2025-05-16/Ganan-Gomez_2022_Nat_Med-GSE137429-anndata-annotated.h5ad
    python anndata_compare_columns.py /wip/scds/delivery-zips/batch17/GSE174653/deliverables/Hayashi_2022_Nature-GSE174653-anndata-annotated.h5ad
    python anndata_compare_columns.py /wip/scds/delivery-zips/batch17/E-MTAB-8562/deliverables/Sun_2020_Nature-E-MTAB-8562-anndata-annotated.h5ad

Output:
    - Indicates if obs columns match or differ, identifying missing or new columns.

Author: Sinu Paul
Created: 2026-02-05
"""

import argparse
from pathlib import Path
import utils


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

    
    utils.compare_obs_columns(h5ad_file_path)


if __name__ == "__main__":
    main()