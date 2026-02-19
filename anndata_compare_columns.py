#!/usr/bin/env python3
"""
compare_columns.py

This script compares the `obs` columns from a reference dataset (provided as a JSON file)
with those of a supplied annotated AnnData (.h5ad) file. It prints out column differences and
writes the observed columns from the provided dataset into a JSON file for record-keeping.
Columns json files from different datasets are stored at /SCDS_TileDB-SOMA/anndata_columns_archive. 
Default dataset used is /SCDS_TileDB-SOMA/anndata_columns_archive/batch14_GSE76312. 
If no other reference dataset is provided, it will be checked against this one and report the changes.

Usage:
    python compare_columns.py [ref_dataset] <current_h5ad_path>

Arguments:
    ref_dataset: batch-dataset combination to be used as the reference, separated by an underscore.
    annotated.h5ad: Path to the AnnData object (.h5ad) for the dataset to compare.

Example:
    python compare_columns.py batch14_GSE76312 /wip/scds/delivery-zips/batch14/GSE137429/deliverables_2025-05-16/Ganan-Gomez_2022_Nat_Med-GSE137429-anndata-annotated.h5ad

Output:
    - Indicates if obs columns match or differ, identifying missing or new columns.
    - Writes a JSON file with columns from the compared dataset for record-keeping.

Author: Sinu Paul
Created: 2026-02-05
"""

import argparse
from pathlib import Path
import scanpy as sc
import json
from copy import deepcopy


def compare_and_save(ref_dataset_path, current_h5ad_path):
    """
    Compares the `obs` columns from a reference dataset JSON file with those of a supplied annotated AnnData (.h5ad) file.

    The function:
        - Loads the reference `obs` columns from a JSON file.
        - Reads the current dataset's `obs` columns from the input .h5ad file.
        - Prints whether the columns match exactly or details the differences:
            - Columns absent in the current dataset with respect to reference.
            - Columns new in the current dataset with respect to reference.
        - Writes a JSON file with the `obs` columns of the current dataset for record-keeping.

    Parameters
    ----------
    ref_dataset_path : pathlib.Path
        Path to the JSON file containing the `obs` columns structure for the reference dataset.
    current_h5ad_path : pathlib.Path
        Path to the .h5ad file to be compared.

    Returns
    -------
    None
        Prints comparison results and writes current `obs` columns to JSON file.
    """

    with ref_dataset_path.open("r", encoding="utf-8") as f:
        ref_obs_columns = json.load(f)['obs']

    current_adata = sc.read_h5ad(current_h5ad_path)
    current_obs_columns = list(current_adata.obs.columns)

    if ref_obs_columns == current_obs_columns:
        print("Columns match.")
    else:
        print("Columns differ!")

        columns_absent = list(set(ref_obs_columns) - set(current_obs_columns))
        columns_new = list(set(current_obs_columns) - set(ref_obs_columns))
        if len(columns_absent) > 0:
            print("Columns absent in current dataset with respect to the reference:")
            for i in range(len(columns_absent)):
                print(str(i+1)+'. '+ columns_absent[i])
        if len(columns_new) > 0:
            print("Columns new in current dataset with respect to the reference:")
            for i in range(len(columns_new)):
                print(str(i+1)+'. '+ columns_new[i])

    current_obs_columns = {
        "obs": current_obs_columns
    }

    current_batch = current_h5ad_path.parent.parent.parent.name
    current_dataset = current_h5ad_path.parent.parent.name
    version_name = current_batch +'_'+ current_dataset
    current_dataset_columns_json_file_path = Path(str(ref_dataset_path.parent) +"/columns_" + version_name + ".json")

    with open(current_dataset_columns_json_file_path, "w") as f:
        json.dump(current_obs_columns, f, indent=2)
    
    print(f"A json file with columns from new dataset has been created at {current_dataset_columns_json_file_path}.")



def main():
    """
    Compares the `.obs` columns of a given AnnData `.h5ad` file against a reference JSON file containing the expected column structure,
    prints differences, and writes the columns of the current file to a new JSON file for archival/comparison purposes.

    Usage:
        python compare_columns.py [ref_dataset] <current_h5ad_path>

    Arguments:
        ref_dataset: str, optional
            Name of the reference dataset whose columns JSON should be used for comparison (e.g., "batch14_GSE76312"). Default is "batch14_GSE76312".
        current_h5ad_path: pathlib.Path
            Path to the AnnData `.h5ad` file to be compared.

    This script will look for the reference JSON in: ./anndata_columns_archive/columns_<ref_dataset>.json

    Output:
        - Prints whether columns match or differ, listing differences if found.
        - Writes a JSON file containing the columns of the current AnnData object to
          ./anndata_columns_archive/columns_<batch>_<dataset>.json, where batch and dataset are inferred from the input file's path.

    Example:
        python compare_columns.py batch14_GSE76312 //wip/scds/delivery-zips/batch14/GSE137429/deliverables_2025-05-16/Ganan-Gomez_2022_Nat_Med-GSE137429-anndata-annotated.h5ad
    """
    parser = argparse.ArgumentParser(description="Compare obs columns of one anndata object with that of a reference/previous anndata object.")
    parser.add_argument(
        "ref_dataset", 
        type=str, 
        nargs='?',
        default='batch14_GSE76312',
        help="Name of the dataset against which the it needs to be checked e.g., batch14_GSE76312. Default is batch14_GSE76312."
    )
    parser.add_argument(
        "current_h5ad_path", 
        type=Path, 
        help="Path to the dataset annotated.h5ad file for which the columns needs to be checked."
    )
    args = parser.parse_args()
    ref_dataset = Path("columns_"+args.ref_dataset+".json")
    ref_dataset_path = Path(__file__).parent/"anndata_columns_archive"/ref_dataset
    current_h5ad_path = args.current_h5ad_path

    print(f"Reference dataset: {ref_dataset_path}")
    print(f"Current dataset to be checked: {current_h5ad_path}")

    if not ref_dataset_path.exists():
        raise FileNotFoundError(f"Reference schema not found: {ref_dataset_path}")

    if not current_h5ad_path.exists():
        raise FileNotFoundError(f"Given dataset annotated.h5ad file not found: {current_h5ad_path}")

    
    compare_and_save(ref_dataset_path, current_h5ad_path)


if __name__ == "__main__":
    main()