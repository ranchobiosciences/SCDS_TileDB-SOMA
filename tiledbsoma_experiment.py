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
import pandas as pd
import tiledbsoma.io
import utils
from utils import is_s3_path, s3_parent, s3_name


def validate_adata(adata, h5ad_file_path):
    """
    Validates an AnnData object before conversion to a TileDB-SOMA experiment.

    Checks:
        - Counts matrix (adata.X) is present.
        - No duplicate cell barcodes in obs index.
        - No duplicate gene names in var index.

    Parameters
    ----------
    adata : AnnData
        The AnnData object to validate.
    h5ad_file_path : str or Path
        Path to the source file, used for error messages.

    Returns
    -------
    bool
        True if all checks pass, False if any check fails.
    """
    errors = []

    if adata.X is None:
        errors.append("counts matrix (adata.X) is None.")

    n_dup_obs = adata.obs_names.duplicated().sum()
    if n_dup_obs > 0:
        errors.append(f"{n_dup_obs} duplicate cell barcodes in obs index.")

    n_dup_var = adata.var_names.duplicated().sum()
    if n_dup_var > 0:
        errors.append(f"{n_dup_var} duplicate gene names in var index.")

    if errors:
        print(f"\nValidation failed for {h5ad_file_path}:")
        for e in errors:
            print(f" - {e}")
        return False

    return True


def compare_obs_columns_and_update_adata(h5ad_file_path: Path):
    """
    
    Compares the `obs` columns from supplied annotated AnnData (.h5ad) file against 
    the standard list of columns provided in file batch17_universal_obs_columns.txt, 
    and updates the AnnData object by adding the absent columns with NA values and dropping the new columns that are not.

    The function:
        - Reads the dataset's `obs` columns from the input .h5ad file.
        - Compares the columns with the standard list and identifies if they match or differ, and if they differ, identifies the columns that are absent in the dataset with respect to the standard list and the columns that are new in the dataset with respect to the standard list.
        - If the columns differ, adds the absent columns to the dataset with NA values and drops the new columns from the dataset that are not in the standard list, and checks if the columns are added/dropped successfully. 
        - Prints out the initial and final number of columns in the dataset.

    Parameters
    ----------
    h5ad_file_path : Path
        Path to the AnnData annotated.h5ad file to be used for comparing the columns and updating the AnnData object.

    Returns
    -------
    adata : AnnData object
        The AnnData object read from the provided .h5ad file, updated with columns to match the standard list.
    
    """

    adata, columns_status, columns_absent, columns_new = utils.compare_obs_columns(h5ad_file_path)
    if columns_status == "differs":
        print("\nInitial number of columns =", len(list(adata.obs.columns)))

        # Add the absent columns to the dataset with NA values and check if they are added successfully
        if len(columns_absent) > 0:
            adata.obs[columns_absent] = pd.DataFrame(pd.NA, index=adata.obs_names, columns=columns_absent)

            # Confirm columns are added
            if all(col in adata.obs.columns for col in columns_absent):
                print("\nAll columns from the standard list are now present in the dataset after adding the absent columns.")
            else:
                print("\nSome columns from the standard list are still missing in the dataset after adding the absent columns.")
                missing = [col for col in columns_absent if col not in adata.obs.columns]
                print("\nMissing columns:")
                for col in missing:
                    print(f" - {col}")

        # Drop the new columns from the dataset that are not in the standard list and check if they are dropped successfully
        if len(columns_new) > 0:
            adata.obs.drop(columns=columns_new, errors="ignore", inplace=True)

            # Confirm columns are dropped
            if all(col not in adata.obs.columns for col in columns_new):
                print("\nAll columns new in the dataset with respect to the standard list are now removed from the dataset.")
            else:
                print("\nSome columns new in the dataset with respect to the standard list are still present in the dataset after dropping the new columns.")
                still_present = [col for col in columns_new if col in adata.obs.columns]
                print("\nColumns still present:")
                for col in still_present:
                    print(f" - {col}")

        print("\nFinal number of columns =", len(list(adata.obs.columns)))
    return adata


def create_tiledbsoma_expt(h5ad_file_path, adata):
    """
    Creates a TileDB-SOMA experiment from the provided AnnData (.h5ad) file.

    The function:
        - Reads the annotated.h5ad AnnData file (e.g., /wip/scds/delivery-zips/batch14/GSE76312/deliverables_2025-05-16/Giustacchini_2017_Nat_Med-GSE76312-anndata-annotated.h5ad).
        - Determines the appropriate output directory (the dataset directory e.g., /wip/scds/delivery-zips/batch16/GSE253006/).
        - Converts the data into a TileDB-SOMA experiment, saving it in the dataset directory with the name 'tiledbsoma_expt' (or 'tiledbsoma_expt_2', etc. if name already exists).
        - Prints progress and the output experiment directory location to stdout.

    Parameters
    ----------
    h5ad_file_path : Path
        Path to the AnnData annotated.h5ad file to be used for creating the TileDB-SOMA experiment.

    adata : AnnData object
        The AnnData object read from the provided .h5ad file, potentially updated with columns

    Returns
    -------
    tiledbsoma_expt_path : str
        The path where the TileDB-SOMA experiment is created.

    """

    #adata = sc.read_h5ad(h5ad_file_path)

    h5ad_str = str(h5ad_file_path)
    if is_s3_path(h5ad_str):
        dataset_path = s3_parent(h5ad_str, levels=2)
        dataset = s3_name(dataset_path)
        batch = s3_name(s3_parent(dataset_path))
        tiledbsoma_expt_base = dataset_path + "/tiledbsoma_expt"
    else:
        dataset_path = Path(h5ad_file_path).parent.parent
        dataset = dataset_path.name
        batch = dataset_path.parent.name
        tiledbsoma_expt_base = str(dataset_path / "tiledbsoma_expt")

    print(f"\nBatch: {batch}, Dataset: {dataset}")
    print(f" - annotated.h5ad file to be used: {h5ad_file_path}")

    tiledbsoma_expt_path = utils.next_available_dir(tiledbsoma_expt_base)

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
        path: Path to the batch/dataset directory that contains the AnnData annotated.h5ad files to be used for creating the TileDB-SOMA experiment 
        (e.g., Batch with multiple datasets: /wip/scds/delivery-zips/batch14/, Individual dataset: /wip/scds/delivery-zips/batch14/GSE76312/)
        Arguments are parsed from the command line. Use --help for usage.

    Raises:
        FileNotFoundError: If the given top-level directory does not exist or if no annotated.h5ad file is found in the search path.

    Example:
        python tiledbsoma_experiment.py /path/to/batch_or_dataset_dir/
    
    """
    parser = argparse.ArgumentParser(description="Generate TileDB-SOMA experiment for the SCDS dataset.")
    parser.add_argument(
        "dir_path",
        type=str,
        help="Path to the dataset directory that contains the AnnData annotated.h5ad file to be used for creating the TileDB-SOMA experiment. Accepts local paths or S3 URIs (s3://bucket/prefix/)."
    )
    args = parser.parse_args()
    dir_path = args.dir_path
    print(f"Given directory path: {dir_path}")

    h5ad_files = []

    if is_s3_path(dir_path):
        fs = utils._get_s3fs()
        # Strip s3:// for s3fs glob operations
        prefix = dir_path[5:].rstrip("/")
        matches = fs.glob(f"{prefix}/**/*annotated.h5ad")
        if not matches:
            raise FileNotFoundError(f"No annotated.h5ad file found at S3 path: {dir_path}")
        h5ad_files = [f"s3://{m}" for m in matches]
    else:
        local_path = Path(dir_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Given directory not found: {dir_path}")
        h5ad_files = [p for p in local_path.rglob("*") if p.is_file() and "annotated.h5ad" in p.name]
        if not h5ad_files:
            raise FileNotFoundError(f"No annotated.h5ad file found in the given directory path.")

    for h5ad_file_path in h5ad_files:
        adata = compare_obs_columns_and_update_adata(h5ad_file_path)
        if not validate_adata(adata, h5ad_file_path):
            print(f" - Skipping conversion for {h5ad_file_path}.\n")
            continue
        tiledbsoma_expt_path = create_tiledbsoma_expt(h5ad_file_path, adata)
        print(f" - TileDB-SOMA experiment created at {tiledbsoma_expt_path}\n")

if __name__ == "__main__":
    main()