#!/usr/bin/env python3


"""
tiledbsoma_experiment.py

Script to generate TileDB-SOMA experiment for SCDS datasets under the given directory (datasets under the batch or individual datasets).

Usage: 
    python tiledbsoma_experiment.py /path/to/dir/

Arguments:
    path: Path to the batch/dataset directory that contains the AnnData annotated.h5ad files to be used for creating the TileDB-SOMA experiment 
    (e.g., Batch with multiple datasets: /wip/scds/delivery-zips/batch14/, Individual dataset: /wip/scds/delivery-zips/batch14/GSE76312/)

Examples:
    Batch with multiple datasets: python tiledbsoma_experiment.py /wip/scds/delivery-zips/batch14/
    Individual dataset: python tiledbsoma_experiment.py /wip/scds/delivery-zips/batch14/GSE76312/ 

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
import scanpy as sc
import tiledbsoma.io


def create_tiledbsoma_expt(h5ad_path):
    """
    Creates a TileDB-SOMA experiment from the provided AnnData (.h5ad) file.

    Parameters
    ----------
    h5ad_path : Path
        Path to the AnnData annotated.h5ad file to be used for creating the TileDB-SOMA experiment.

    This function reads the annotated.h5ad AnnData file (e.g., /wip/scds/delivery-zips/batch14/GSE76312/deliverables_2025-05-16/Giustacchini_2017_Nat_Med-GSE76312-anndata-annotated.h5ad), 
    determines the appropriate output directory (the dataset directory e.g., /wip/scds/delivery-zips/batch16/GSE253006/),
    and converts the data into a TileDB-SOMA experiment, saving it in the dataset directory.
    """

    adata = sc.read_h5ad(h5ad_path)

    dataset_path = h5ad_path.parent.parent
    dataset = dataset_path.name
    batch_path = dataset_path.parent
    batch = batch_path.name
    print(f"\nBatch: {batch}, Dataset: {dataset}")
    print(f" - annotated.h5ad file to be used: {h5ad_path}")
    tiledbsoma_expt_path = dataset_path/"tiledbsoma_expt"

    tiledbsoma_expt_path = str(utils.next_available_dir(tiledbsoma_expt_path))

    tiledbsoma.io.from_anndata(
    experiment_uri=tiledbsoma_expt_path,
    anndata=adata,
    measurement_name="RNA"
    )

    return(tiledbsoma_expt_path)


def main():
    """
    Main function to generate TileDB-SOMA experiment(s) for SCDS datasets.

    This script takes a directory path (either a batch-level directory containing multiple datasets,
    or an individual dataset directory) as input, searches recursively for AnnData
    annotated .h5ad files within that directory, and for each such file found,
    creates a TileDB-SOMA experiment in the corresponding dataset directory.

    - For each annotated.h5ad file found:
        - The experiment will be created in a subdirectory called 'tiledbsoma_expt'
          (or 'tiledbsoma_expt_2', etc. if name already exists) next to the h5ad file.
        - The operation prints progress and the output experiment directory location to stdout.

    Args:
        None. Arguments are parsed from the command line. Use --help for usage.

    Raises:
        FileNotFoundError: If the given top-level directory does not exist or if
        no annotated.h5ad file is found in the search path.

    Example:
        python tiledbsoma_experiment.py /path/to/batch_or_dataset_dir/
    """
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

            tiledbsoma_expt_path = create_tiledbsoma_expt(h5ad_path)
            print(f" - TileDB-SOMA experiment created at {tiledbsoma_expt_path}\n")

    if h5ad_path == '':
        raise FileNotFoundError(f"No annotated.h5ad file found in the given directory path.")

if __name__ == "__main__":
    main()