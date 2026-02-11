#!/usr/bin/env python3


"""

tiledbsoma_expt.py

Script to generate TileDB-SOMA experiment for SCDS datasets under the given directory (datasets under the batch or individual datasets).

Usage: 
    python tiledbsoma_expt.py /path/to/dir/

Arguments:
    path: Path to the batch/dataset directory that contains the AnnData annotated.h5ad files to be used for creating the TileDB-SOMA experiment 
    (e.g., Batch with multiple datasets: /wip/scds/delivery-zips/batch14/, Individual dataset: /wip/scds/delivery-zips/batch14/GSE76312/)

Examples:
    Batch with multiple datasets: python tiledbsoma_expt_dataset.py /wip/scds/delivery-zips/batch14/
    Individual dataset: python tiledbsoma_expt_dataset.py /wip/scds/delivery-zips/batch14/GSE76312/ 

Output:
    A TileDB-SOMA experiment directory in the dataset directory (e.g., /wip/scds/delivery-zips/batch14/GSE76312/tiledbsoma_expt)
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
        "dir_path", 
        type=Path, 
        help="Path to the dataset directory that contains the AnnData annotated.h5ad file to be used for creating the TileDB-SOMA experiment"
        )
    args = parser.parse_args()
    dir_path = args.dir_path
    print(f"Given directory path: {dir_path}")

    if not dir_path.exists():
        raise FileNotFoundError(f"Given directory not found: {dir_path}")

    h5ad_path = ''
    for path in dir_path.rglob("*"):
        if path.is_file() and 'annotated.h5ad' in path.name:
            h5ad_path = path

            tiledbsoma_expt_path = utils.create_tiledbsoma_expt(h5ad_path)
            print(f" - TileDB-SOMA experiment created at {tiledbsoma_expt_path}\n")

    if h5ad_path == '':
        raise FileNotFoundError(f"No annotated.h5ad file found in the given directory path.")

if __name__ == "__main__":
    main()