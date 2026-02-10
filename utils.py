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
            print(f"- {path} already exists. The TileDB-SOMA experiment will be created at {new_path}")
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

