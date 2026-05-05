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


from pathlib import Path
import sys
import scanpy as sc


class _Tee:
    """Duplicates writes to both a stream (e.g. stdout) and a log file."""

    def __init__(self, stream, log_path: str):
        self._stream = stream
        self._log = open(log_path, "w", buffering=1)

    def write(self, data):
        self._stream.write(data)
        self._log.write(data)

    def flush(self):
        self._stream.flush()
        self._log.flush()

    def close(self):
        self._log.close()


def setup_logging(log_path: str):
    """Redirect stdout to write to both the terminal and log_path."""
    sys.stdout = _Tee(sys.stdout, log_path)


def teardown_logging():
    """Restore stdout and close the log file if logging was set up."""
    if isinstance(sys.stdout, _Tee):
        tee = sys.stdout
        sys.stdout = tee._stream
        tee.close()


def is_s3_path(path: str) -> bool:
    """Returns True if the given path is an S3 URI (starts with s3://)."""
    return str(path).startswith("s3://")


def _get_s3fs():
    """Lazily import and return an s3fs.S3FileSystem instance."""
    try:
        import s3fs
    except ImportError:
        raise ImportError("s3fs is required for S3 support. Install it with: conda install -c conda-forge s3fs")
    return s3fs.S3FileSystem()


def s3_parent(s3_uri: str, levels: int = 1) -> str:
    """Return the parent path of an S3 URI by removing N trailing path components."""
    assert s3_uri.startswith("s3://"), f"Expected S3 URI, got: {s3_uri}"
    parts = s3_uri.rstrip("/").split("/")
    return "/".join(parts[:-levels])


def s3_name(s3_uri: str) -> str:
    """Return the final path component of an S3 URI."""
    return s3_uri.rstrip("/").split("/")[-1]


def next_available_dir(path) -> str:
    """
    Returns the next available directory path by appending an incrementing number as suffix if the given path exists.
    This function will check if the given directory (e.g., tiledbsoma_expt) already exists, and will return tiledbsoma_expt_2 (1 is skipped deliberately)

    Supports both local filesystem paths and S3 URIs (s3://bucket/prefix).

    Parameters
    ----------
    path : str or Path
        The base directory path to check.

    Returns
    -------
    str
        The next available directory path.
    """
    path_str = str(path)
    if is_s3_path(path_str):
        fs = _get_s3fs()
        if not fs.exists(path_str):
            return path_str
        i = 2
        while True:
            new_path = f"{path_str}_{i}"
            if not fs.exists(new_path):
                print(f" - {path_str} already exists. The TileDB-SOMA experiment will be created at {new_path}")
                return new_path
            i += 1
    else:
        path = Path(path)
        if not path.exists():
            return str(path)
        i = 2
        while True:
            new_path = Path(f"{path}_{i}")
            if not new_path.exists():
                print(f" - {path} already exists. The TileDB-SOMA experiment will be created at {new_path}")
                return str(new_path)
            i += 1

VAR_NUMERIC_COLUMNS = {"means", "dispersions", "dispersions_norm", "mean", "std"}


def compare_var_columns(adata, columns_file: str = None):
    """
    Compares the `var` columns of the given AnnData object against a standard
    list of columns. Defaults to batch17_universal_var_columns.txt.

    Parameters
    ----------
    adata : AnnData
        The AnnData object whose var columns will be compared.
    columns_file : str, optional
        Path to the standard columns file. Defaults to batch17_universal_var_columns.txt.

    Returns
    -------
    columns_status : str
        "matches" or "differs".
    columns_absent : list
        Columns absent in the current dataset relative to the standard list.
    columns_new : list
        Columns present in the current dataset but not in the standard list.
    """
    standard_columns_file_path = Path(columns_file) if columns_file else Path(__file__).parent / "batch17_universal_var_columns.txt"

    with open(standard_columns_file_path, "r") as f:
        std_columns = [line.strip() for line in f if line.strip() != '']

    print('Number of standard var columns =', len(std_columns))

    adata_columns = list(adata.var.columns)

    columns_status = "matches"
    columns_absent = []
    columns_new = []

    if set(std_columns) == set(adata_columns):
        print("\nVar columns match with the standard list.")
    else:
        print("\nVar columns differ from the standard list.")
        columns_status = "differs"

        columns_absent = list(set(std_columns) - set(adata_columns))
        columns_new = list(set(adata_columns) - set(std_columns))
        if len(columns_absent) > 0:
            print("\nVar columns absent in dataset with respect to the standard list:")
            for i, col in enumerate(columns_absent):
                print(str(i + 1) + '. ' + col)
        if len(columns_new) > 0:
            print("\nVar columns new in dataset with respect to the standard list:")
            for i, col in enumerate(columns_new):
                print(str(i + 1) + '. ' + col)

    return columns_status, columns_absent, columns_new


def compare_obs_columns(h5ad_file_path: Path, columns_file: str = None):
    """
    Compares the `obs` columns from supplied annotated AnnData (.h5ad) file against
    a standard list of columns. Defaults to batch17_universal_obs_columns.txt.

    Parameters
    ----------
    h5ad_file_path : pathlib.Path
        Path to the .h5ad file to be compared.
    columns_file : str, optional
        Path to the standard columns file. Defaults to batch17_universal_obs_columns.txt.

    Returns
    -------
    adata : AnnData object
        The AnnData object read from the provided .h5ad file.
    columns_status : str
        "matches" or "differs".
    columns_absent : list
        Columns absent in the current dataset relative to the standard list.
    columns_new : list
        Columns present in the current dataset but not in the standard list.
    """

    standard_columns_file_path = Path(columns_file) if columns_file else Path(__file__).parent / "batch17_universal_obs_columns.txt"

    with open(standard_columns_file_path, "r") as f:
        std_columns = [line.strip() for line in f if line.strip() != '']
    
    print('Number of standard columns =', len(std_columns))

    if is_s3_path(str(h5ad_file_path)):
        fs = _get_s3fs()
        with fs.open(str(h5ad_file_path), "rb") as f:
            adata = sc.read_h5ad(f)
    else:
        adata = sc.read_h5ad(h5ad_file_path)
    adata_columns = list(adata.obs.columns)

    columns_status = "matches"
    columns_absent = []
    columns_new = []

    if set(std_columns) == set(adata_columns):
        print("\nColumns match with the standard list.")
    else:
        print("\nColumns differ from the standard list.")
        columns_status = "differs"

        columns_absent = list(set(std_columns) - set(adata_columns))
        columns_new = list(set(adata_columns) - set(std_columns))
        if len(columns_absent) > 0:
            print("\nColumns absent in dataset with respect to the standard list:")
            for i in range(len(columns_absent)):
                print(str(i+1)+'. '+ columns_absent[i])
        if len(columns_new) > 0:
            print("\nColumns new in dataset with respect to the standard list:")
            for i in range(len(columns_new)):
                print(str(i+1)+'. '+ columns_new[i])
    return adata, columns_status, columns_absent, columns_new