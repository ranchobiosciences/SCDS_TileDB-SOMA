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
import numpy as np
import pandas as pd
import scipy.sparse
import tiledbsoma.io
import utils
from utils import is_s3_path, s3_parent, s3_name, VAR_NUMERIC_COLUMNS, setup_logging, teardown_logging

DATASET_GROUP_OBS_COLUMNS_FILE = {
    "scds": "batch17_universal_obs_columns.txt",
    "scrnalive": "scrnalive_universal_obs_columns.txt",
}

DATASET_GROUP_VAR_COLUMNS_FILE = {
    "scds": "batch17_universal_var_columns.txt",
    "scrnalive": "scrnalive_universal_var_columns.txt",
}


def normalize_obsm(adata):
    """
    Normalizes obsm entries in-place to be compatible with TileDB-SOMA conversion.

    tiledbsoma.io.from_anndata() requires obsm entries to be dense numeric numpy
    arrays. This function:
        - Converts pandas DataFrames to numpy arrays.
        - Converts scipy sparse matrices to dense numpy arrays.
        - Drops entries with non-numeric dtypes (e.g., object/string arrays),
          printing a warning for each dropped entry.

    Parameters
    ----------
    adata : AnnData
        The AnnData object whose obsm will be normalized in-place.
    """
    keys_to_drop = []
    for key, value in adata.obsm.items():
        if isinstance(value, pd.DataFrame):
            adata.obsm[key] = value.to_numpy()
            print(f" - obsm['{key}']: converted DataFrame to numpy array.")
        elif scipy.sparse.issparse(value):
            adata.obsm[key] = value.toarray()
            print(f" - obsm['{key}']: converted sparse matrix to dense numpy array.")

        # After any conversion, check dtype is numeric
        arr = adata.obsm[key]
        if not np.issubdtype(np.array(arr).dtype, np.number):
            print(f" - obsm['{key}']: non-numeric dtype '{np.array(arr).dtype}' is not supported by TileDB-SOMA — dropping.")
            keys_to_drop.append(key)

    for key in keys_to_drop:
        del adata.obsm[key]


def map_uns_category_orders(adata):
    """
    For each key in adata.uns ending in '_colors', checks whether a matching
    column exists in adata.obs. If found, writes the ordered category labels
    to a new adata.uns key with the same base name but ending in '_order'.

    This ensures the color-to-label mapping is explicitly preserved in uns
    before conversion to TileDB-SOMA, since color arrays are index-ordered
    against the category list.

    For categorical obs columns the order comes from the defined category
    order (adata.obs[col].cat.categories). For non-categorical columns the
    unique values are sorted for consistency.

    If the color array is longer than the category list (e.g., the dataset
    was filtered after colors were assigned), the colors are trimmed to match.
    If colors are fewer than categories, the entry is skipped with a warning.

    Parameters
    ----------
    adata : AnnData
        The AnnData object to update in-place.
    """
    for key in list(adata.uns.keys()):
        if not key.endswith("_colors"):
            continue
        obs_col = key[: -len("_colors")]
        if obs_col not in adata.obs.columns:
            continue

        col = adata.obs[obs_col]
        if hasattr(col, "cat"):
            categories = list(col.cat.categories)
        else:
            categories = sorted(col.dropna().unique().tolist())

        n_colors = len(adata.uns[key])
        if n_colors != len(categories):
            if n_colors > len(categories):
                print(f" - uns['{key}']: color count ({n_colors}) exceeds category count ({len(categories)}) for obs column '{obs_col}' — trimming colors to match.")
                adata.uns[key] = adata.uns[key][: len(categories)]
            else:
                print(f" - uns['{key}']: color count ({n_colors}) is less than category count ({len(categories)}) for obs column '{obs_col}' — skipping.")
                continue

        order_key = obs_col + "_order"
        adata.uns[order_key] = categories
        print(f" - uns['{order_key}']: saved {len(categories)} category labels for '{obs_col}'.")


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


def compare_obs_columns_and_update_adata(h5ad_file_path: Path, dataset_group: str = "scds"):
    """
    Compares the `obs` columns from the supplied .h5ad file against the standard list
    for the given dataset group, then updates the AnnData object by adding absent columns
    with NaN values and dropping extra columns not in the standard list.

    Parameters
    ----------
    h5ad_file_path : Path
        Path to the AnnData annotated.h5ad file.
    dataset_group : str
        Dataset group determining which standard columns file to use ("scds" or "scrnalive").

    Returns
    -------
    adata : AnnData object
        The AnnData object updated to match the standard column list.
    """
    columns_file = str(Path(__file__).parent / DATASET_GROUP_OBS_COLUMNS_FILE[dataset_group])
    adata, columns_status, columns_absent, columns_new = utils.compare_obs_columns(h5ad_file_path, columns_file=columns_file)
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


def compare_var_columns_and_update_adata(adata, dataset_group: str = "scds"):
    """
    Compares the `var` columns of the given AnnData object against the standard list
    for the given dataset group, then updates the object in-place by adding absent columns
    (numeric columns filled with np.nan, all others with pd.NA) and dropping extra columns.

    Parameters
    ----------
    adata : AnnData
        The AnnData object to update.
    dataset_group : str
        Dataset group determining which standard columns file to use ("scds" or "scrnalive").

    Returns
    -------
    adata : AnnData
        The updated AnnData object.
    """
    columns_file = str(Path(__file__).parent / DATASET_GROUP_VAR_COLUMNS_FILE[dataset_group])
    columns_status, columns_absent, columns_new = utils.compare_var_columns(adata, columns_file=columns_file)
    if columns_status == "differs":
        print("\nInitial number of var columns =", len(list(adata.var.columns)))

        if len(columns_absent) > 0:
            numeric_absent = [col for col in columns_absent if col in VAR_NUMERIC_COLUMNS]
            string_absent = [col for col in columns_absent if col not in VAR_NUMERIC_COLUMNS]

            if string_absent:
                adata.var[string_absent] = pd.DataFrame(pd.NA, index=adata.var_names, columns=string_absent)
            if numeric_absent:
                adata.var[numeric_absent] = pd.DataFrame(np.nan, index=adata.var_names, columns=numeric_absent)

            if all(col in adata.var.columns for col in columns_absent):
                print("\nAll var columns from the standard list are now present in the dataset after adding the absent columns.")
            else:
                print("\nSome var columns from the standard list are still missing in the dataset after adding the absent columns.")
                missing = [col for col in columns_absent if col not in adata.var.columns]
                print("\nMissing var columns:")
                for col in missing:
                    print(f" - {col}")

        if len(columns_new) > 0:
            adata.var.drop(columns=columns_new, errors="ignore", inplace=True)

            if all(col not in adata.var.columns for col in columns_new):
                print("\nAll extra var columns not in the standard list have been removed from the dataset.")
            else:
                print("\nSome extra var columns are still present after dropping.")
                still_present = [col for col in columns_new if col in adata.var.columns]
                print("\nVar columns still present:")
                for col in still_present:
                    print(f" - {col}")

        print("\nFinal number of var columns =", len(list(adata.var.columns)))
    return adata


def create_tiledbsoma_expt(h5ad_file_path, adata, output_dir=None):
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

    output_dir : str, optional
        Root directory under which experiments are written as {output_dir}/{batch}/{dataset}/tiledbsoma_expt.
        Accepts local paths or S3 URIs. If not provided, experiments are written next to the input h5ad files.

    Returns
    -------
    tiledbsoma_expt_path : str
        The path where the TileDB-SOMA experiment is created.

    """

    h5ad_str = str(h5ad_file_path)
    if is_s3_path(h5ad_str):
        dataset_path = s3_parent(h5ad_str, levels=2)
        dataset = s3_name(dataset_path)
        batch = s3_name(s3_parent(dataset_path))
        if output_dir is not None:
            tiledbsoma_expt_base = output_dir.rstrip("/") + "/" + batch + "/" + dataset + "/tiledbsoma_expt"
        else:
            tiledbsoma_expt_base = dataset_path + "/tiledbsoma_expt"
    else:
        dataset_path = Path(h5ad_file_path).parent.parent
        dataset = dataset_path.name
        batch = dataset_path.parent.name
        if output_dir is not None:
            tiledbsoma_expt_base = str(Path(output_dir) / batch / dataset / "tiledbsoma_expt")
        else:
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
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Root output directory. Experiments are written to {output}/{batch}/{dataset}/tiledbsoma_expt. Accepts local paths or S3 URIs. Defaults to writing next to the input h5ad files."
    )
    parser.add_argument(
        "--dataset-group",
        type=str,
        default="scds",
        choices=["scds", "scrnalive"],
        help="Dataset group, which determines the standard obs/var column files used (default: scds)."
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Path to log file. If provided, output is written to both stdout and the log file."
    )
    args = parser.parse_args()

    if args.log_file:
        setup_logging(args.log_file)

    try:
        _main(args)
    finally:
        teardown_logging()


def _main(args):
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
        adata = compare_obs_columns_and_update_adata(h5ad_file_path, dataset_group=args.dataset_group)
        adata = compare_var_columns_and_update_adata(adata, dataset_group=args.dataset_group)
        normalize_obsm(adata)
        map_uns_category_orders(adata)
        if not validate_adata(adata, h5ad_file_path):
            print(f" - Skipping conversion for {h5ad_file_path}.\n")
            continue
        tiledbsoma_expt_path = create_tiledbsoma_expt(h5ad_file_path, adata, output_dir=args.output)
        print(f" - TileDB-SOMA experiment created at {tiledbsoma_expt_path}\n")

if __name__ == "__main__":
    main()