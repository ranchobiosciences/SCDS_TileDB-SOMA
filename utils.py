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


#import os
from pathlib import Path
import tiledbsoma as soma
import tiledbsoma.io
#import tiledb
import scanpy as sc
#import pandas as pd
#import matplotlib.pyplot as plt
from scipy.sparse import issparse


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

    tiledbsoma_expt_path = str(next_available_dir(tiledbsoma_expt_path))

    tiledbsoma.io.from_anndata(
    experiment_uri=tiledbsoma_expt_path,
    anndata=adata,
    measurement_name="RNA"
    )

    return(tiledbsoma_expt_path)


def extract_adata_schema(adata):
    """
    Extracts a comprehensive schema from the provided AnnData object including columns, keys and their data types.

    Parameters
    ----------
    adata : AnnData

    Returns
    -------
    dict
        Dictionary containing schema information for X, obs, var, uns, obsm, varm, and obsp, 
        including datatypes, number of dimensions, and keys for each attribute group.
    """
    return {
        "schema": {
            "X": {
                "ndim": adata.X.ndim,
                "dtype": str(adata.X.dtype),
            },

            "obs": {
                "columns": {
                    col: str(dtype)
                    for col, dtype in adata.obs.dtypes.items()
                }
            },

            "var": {
                "columns": {
                    col: str(dtype)
                    for col, dtype in adata.var.dtypes.items()
                }
            },

            "uns": {
                "keys": {
                    key: type(value).__name__
                    for key, value in adata.uns.items()
                }
            },

            "obsm": {
                key: {
                    "ndim": value.ndim,
                    "dtype": str(value.dtype),
                }
                for key, value in adata.obsm.items()
            },

            "varm": {
                key: {
                    "ndim": value.ndim,
                    "dtype": str(value.dtype),
                }
                for key, value in adata.varm.items()
            },

            "obsp": {
                key: {
                    "ndim": value.ndim,
                    "dtype": str(value.dtype),
                    "sparse": issparse(value),
                }
                for key, value in adata.obsp.items()
            },

            "layers": {
                key: {
                    "ndim": value.ndim,
                    "dtype": str(value.dtype),
                }
                for key, value in adata.layers.items()
            }
        }
    }