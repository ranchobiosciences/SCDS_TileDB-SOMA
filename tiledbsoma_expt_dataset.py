#!/usr/bin/env python3


"""

tiledbsoma_expt_dataset.py

Script to generate TileDB-SOMA experiment for individual SCDS dataset (e.g., GSE76312).

Usage: python tiledbsoma_expt_dataset.py /path/to/dataset_dir/

Arguments:
    dataset_path: Path to the dataset directory that contains the AnnData annotated.h5ad file to be used for 
    creating the TileDB-SOMA experiment (e.g., /wip/scds/delivery-zips/batch14/GSE76312/)

Example:
    python tiledbsoma_expt_dataset.py /wip/scds/delivery-zips/batch14/GSE76312/ 

Output:
    A TileDB-SOMA experiment folder in the dataset directory (e.g., /wip/scds/delivery-zips/batch14/GSE76312/tiledbsoma_expt)
    If the directory name already exists, it will use the next available directory path by appending an incrementing number as suffix 
    (e.g., /wip/scds/delivery-zips/batch14/GSE76312/tiledbsoma_expt_2).

Author: Sinu Paul
Created: 2026-02-05

"""


import argparse
from pathlib import Path
import utils


def main():
    parser = argparse.ArgumentParser(description="Generate TileDB-SOMA experiment for the SCDS dataset.")
    parser.add_argument(
        "dataset_path", 
        type=Path, 
        help="Path to the dataset directory that contains the AnnData annotated.h5ad file to be used for creating the TileDB-SOMA experiment"
        )
    args = parser.parse_args()
    dataset_path = args.dataset_path
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_path}")

    h5ad_path = ''
    for path in dataset_path.rglob("*"):
        if path.is_file() and 'annotated.h5ad' in path.name:
            h5ad_path = path
            print(f"- annotated.h5ad file to be used: {h5ad_path}")
    
    if h5ad_path == '':
        raise FileNotFoundError(f"annotated.h5ad file not found in the given dataset directory.")

    tiledbsoma_expt_path = utils.create_tiledbsoma_expt(h5ad_path)
    print(f"- TileDB-SOMA experiment has been created at {tiledbsoma_expt_path}")


if __name__ == "__main__":
    main()