#!/usr/bin/env python3


"""

tiledbsoma_expt_dataset.py

Script to generate TileDB-SOMA experiment for individual scds dataset (e.g., GSE76312).

Usage: python tiledbsoma_expt_dataset.py /path/to/dataset_dir/
Arguments:
    dataset_path: Path to the dataset directory that contains the AnnData annotated.h5ad file to be used for 
    creating the TileDB-SOMA experiment (e.g., /wip/scds/delivery-zips/batch14/GSE76312/)

Example:
    python tiledbsoma_expt_dataset.py /wip/scds/delivery-zips/batch14/GSE76312/ 

Output:
    A TileDB-SOMA experiment folder in the dataset directory (e.g., /wip/scds/delivery-zips/batch14/GSE76312/tiledbsoma_expt)
    If the directory name already exists, it will use the next available directory path by appending an incrementing number as suffix.

Author: Sinu Paul
Created: 2026-02-05

"""


import os
import argparse
from pathlib import Path
import tiledbsoma as soma
import tiledbsoma.io
import tiledb
import scanpy as sc
import pandas as pd
import matplotlib.pyplot as plt


def next_available_dir(path: Path) -> Path:
    """
    Returns the next available directory path by appending an incrementing number as suffix if the given path exists.

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
            return new_path
        i += 1


def create_tiledbsoma_expt(h5ad_path):
    """
    Creates a TileDB-SOMA experiment from the provided AnnData (.h5ad) file.

    Parameters
    ----------
    dataset_path : Path
        Path to the dataset directory that contains the AnnData annotated.h5ad file to be used for creating the TileDB-SOMA experiment.

    This function reads the "annotated.h5ad" AnnData file, determines the appropriate output directory,
    and converts the data into a TileDB-SOMA experiment, saving it in the dataset directory.
    """

    adata = sc.read_h5ad(h5ad_path)

    dataset_path = h5ad_path.parent.parent
    tiledbsoma_expt_path = dataset_path/"tiledbsoma_expt"

    tiledbsoma_expt_path = str(next_available_dir(tiledbsoma_expt_path))

    tiledbsoma.io.from_anndata(
    experiment_uri=tiledbsoma_expt_path,
    anndata=adata,
    measurement_name="RNA"
    )

    return(tiledbsoma_expt_path)


def main():
    parser = argparse.ArgumentParser(description="Generate TileDB-SOMA experiment for the scds dataset.")
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
            print(f"annotated.h5ad file to be used: {h5ad_path}")
    
    if h5ad_path == '':
        raise FileNotFoundError(f"annotated.h5ad file not found in the given dataset directory.")

    tiledbsoma_expt_path = create_tiledbsoma_expt(h5ad_path)
    print(f"TileDB-SOMA experiment has been created at {tiledbsoma_expt_path}")


if __name__ == "__main__":
    main()