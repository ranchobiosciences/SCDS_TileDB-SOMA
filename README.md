# SCDS_TileDB-SOMA
Scripts to create TileDB-SOMA experiment, add experiments to collections etc. for Single cell datasets

Use conda env `tiledbsoma` (`/opt/mamba/envs/tiledbsoma/`) on scds-c server:  
`conda activate tiledbsoma`  

Can create the environment from the `tiledbsoma_environment.yml` file included in the repo:  
`conda env create -f tiledbsoma_environment.yml`

## tiledbsoma_experiment.py
Script to generate TileDB-SOMA experiment for SCDS datasets under the given directory (datasets under the batch or individual datasets).

Usage:  
    `python tiledbsoma_experiment.py /path/to/dir/`

Arguments:  
- path: Path to the batch or dataset directory that contains the AnnData `-annotated.h5ad` files to be used for creating the TileDB-SOMA experiment 
    (e.g., Batch with multiple datasets: `/wip/scds/delivery-zips/batch14/`, Individual dataset: `/wip/scds/delivery-zips/batch14/GSE76312/`)

Examples:  
- Batch with multiple datasets: `python tiledbsoma_experiment.py /wip/scds/delivery-zips/batch14/`  
- Individual dataset: `python tiledbsoma_experiment.py /wip/scds/delivery-zips/batch14/GSE76312/`  

Output:  
- A TileDB-SOMA experiment directory in the dataset directory (e.g., `/wip/scds/delivery-zips/batch14/GSE76312/tiledbsoma_expt`)
    If the directory name already exists, it will use the next available directory path by appending an incrementing number as suffix 
    (e.g., `/wip/scds/delivery-zips/batch14/GSE76312/tiledbsoma_expt_2`).

## tiledbsoma_collection.py
Script to add TileDB-SOMA experiments to the appropriate collection based on donor organism and dataset workflow.

Usage:
`python tiledbsoma_collection.py /path/to/dir/`

Arguments:
- dir_path: Path to the directory with TileDB-SOMA experiments that needs to be added to the collection. It can be a batch dir or tiledbsoma_expt directory.  

Behavior:  
  - Opens the TileDB-SOMA experiment and reads required metadata (donor organism, dataset workflow).  
  - Determines appropriate collection (`Human_10x`, `Human_ss2`, `Mouse_10x`, `Mouse_ss2`) from metadata (the collections are located at `/wip/scds/delivery-zips/tiledbsoma_collections/`).  
  - Adds or links the experiment to the determined collection in the default collections directory.  

Examples:
- For adding one TileDB-SOMA experiment: `python tiledbsoma_collection.py /wip/scds/delivery-zips/batch14/GSE76312/tiledbsoma_expt`
- For adding multiple TileDB-SOMA experiments under a batch: `python tiledbsoma_collection.py /wip/scds/delivery-zips/batch14/`

## anndata_compare_columns.py
This script compares the `obs` columns from a reference dataset (provided as a JSON file)
with those of a supplied annotated AnnData (.h5ad) file. It prints out column differences and
writes the observed columns from the provided dataset into a JSON file for record-keeping.
Columns json files from different datasets are stored at /SCDS_TileDB-SOMA/anndata_columns_archive. 
Default dataset used is /SCDS_TileDB-SOMA/anndata_columns_archive/batch14_GSE76312. 
If no other reference dataset is provided, it will be checked against this one and report the changes.

Usage:  
`python compare_columns.py ref_dataset /path/to/h5ad`

Arguments:  
- ref_dataset: batch-dataset combination to be used as the reference, separated by an underscore e.g., batch14_GSE76312.
- annotated.h5ad: Path to the AnnData object (.h5ad) for the dataset to compare.

Example:  
    `python compare_columns.py batch14_GSE76312 /wip/scds/delivery-zips/batch14/GSE137429/deliverables_2025-05-16/Ganan-Gomez_2022_Nat_Med-GSE137429-anndata-annotated.h5ad`

Output:  
  - Indicates if obs columns match or differ, identifying missing or new columns.
  - Writes a JSON file with columns from the compared dataset for record-keeping.
