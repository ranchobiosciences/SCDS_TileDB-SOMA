# SCDS_TileDB-SOMA
Scripts to create TileDB-SOMA experiments, collections, add experiments to collections do analysis for single cell datasets.

Use conda env `tiledbsoma` (`/opt/mamba/envs/tiledbsoma/`) on scds-c server:  
`conda activate tiledbsoma`  

Can create the environment from the `tiledbsoma_environment.yml` file included in the repo:  
`conda env create -f tiledbsoma_environment.yml`

## tiledbsoma_experiment.py
Script to generate TileDB-SOMA experiment for SCDS datasets (datasets under the batch dir or individual datasets).

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
This script compares the `obs` columns from a supplied annotated AnnData (.h5ad) file against the standard list of columns provided in file batch17_universal_obs_columns.txt. It prints out column differences.

Usage:  
`python compare_columns.py /path/to/h5ad_file`

Arguments:  
  - h5ad_file_path: Path to the h5ad file to be compared.

Example:  
    `python compare_columns.py batch14_GSE76312 /wip/scds/delivery-zips/batch14/GSE137429/deliverables_2025-05-16/Ganan-Gomez_2022_Nat_Med-GSE137429-anndata-annotated.h5ad`
    `python anndata_compare_columns.py /wip/scds/delivery-zips/batch17/GSE174653/deliverables/Hayashi_2022_Nature-GSE174653-anndata-annotated.h5ad`
    `python anndata_compare_columns.py /wip/scds/delivery-zips/batch17/E-MTAB-8562/deliverables/Sun_2020_Nature-E-MTAB-8562-anndata-annotated.h5ad1

Output:  
  - Indicates if obs columns match or differ, identifying missing or new columns.
  
