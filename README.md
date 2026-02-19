# SCDS_TileDB-SOMA
Scripts to create TileDB-SOMA experiment, collections etc for Single cell datasets

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
