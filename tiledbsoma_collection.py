#!/usr/bin/env python3

"""
tiledbsoma_collection.py

Script to add TileDB-SOMA experiments to the appropriate collection based on donor organism and dataset workflow.

Usage:
    python tiledbsoma_collection.py /path/to/dir/

Arguments:
    dir_path: Path to the directory with TileDB-SOMA experiments that needs to be added to the collection. It can be a batch dir or tiledbsoma_expt directory.

Behavior:
    - Opens the TileDB-SOMA experiment and reads required metadata (donor organism, dataset workflow).
    - Determines appropriate collection (Human_10x, Human_ss2, Mouse_10x, Mouse_ss2) from metadata 
    (the collections are located at /wip/scds/delivery-zips/tiledbsoma_collections/).
    - Adds or links the experiment to the determined collection in the default collections directory.

Example:
    For adding one TileDB-SOMA experiment: python tiledbsoma_collection.py /wip/scds/delivery-zips/batch14/GSE76312/tiledbsoma_expt
    For adding multiple TileDB-SOMA experiments under a batch: python tiledbsoma_collection.py /wip/scds/delivery-zips/batch14/
    
Author: Sinu Paul
Created: 2026-02-05
"""


import argparse
from pathlib import Path
import tiledbsoma as soma
import utils
from utils import is_s3_path, s3_parent, s3_name, setup_logging, teardown_logging

# Expected gene counts for ss2 datasets by organism
SS2_EXPECTED_GENES = {
    "human": 36522,
    "mouse": 31992,
}

# Dataset-specific gene count exceptions for ss2 datasets
SS2_DATASET_EXCEPTIONS = {
    "GSE84465": 36601,
}

# Expected number of genes (vars) for cellranger-processed datasets
CELLRANGER_EXPECTED_GENES = {
    "human": 36601,
    "mouse": 32285,
    "cynomolgus monkey": 22316,
    "rhesus monkey": 26530,
}

ORGANISM_COLLECTION_PREFIX = {
    "human": "Human",
    "mouse": "Mouse",
    "cynomolgus monkey": "Cynomolgus",
    "rhesus monkey": "Rhesus",
}


def main():

    parser = argparse.ArgumentParser(description="Add TileDB-SOMA experiments to the appropriate collection (Human_10x/Human_ss2/Mouse_10x/Mouse_ss2).")
    parser.add_argument(
        "dir_path",
        type=str,
        help="Path to the directory with TileDB-SOMA experiments that needs to be added to the collection. Accepts local paths or S3 URIs (s3://bucket/prefix/)."
    )
    parser.add_argument(
        "--collections-path",
        type=str,
        default="/wip/scds/delivery-zips/tiledbsoma_collections/",
        help="Path to the root collections directory. Accepts local paths or S3 URIs. Defaults to /wip/scds/delivery-zips/tiledbsoma_collections/."
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
    collections_path = args.collections_path.rstrip("/")
    print(f"Given TileDB-SOMA experiments directory path: {dir_path}")
    print(f"Collections path: {collections_path}")

    # Build list of tiledbsoma_expt URIs to process
    expt_uris = []

    if is_s3_path(dir_path):
        fs = utils._get_s3fs()
        prefix = dir_path[5:].rstrip("/")
        dir_name = prefix.split("/")[-1]

        if dir_name == "tiledbsoma_expt":
            # dir_path points directly to an experiment
            expt_uris = [dir_path]
        else:
            # Find all tiledbsoma_expt directories by locating the TileDB group marker
            markers = fs.glob(f"{prefix}/**/tiledbsoma_expt/__tiledb_group.tdb")
            expt_uris = [f"s3://{m.rsplit('/__tiledb_group.tdb', 1)[0]}" for m in markers]

        if not expt_uris:
            raise FileNotFoundError(f"No tiledbsoma_expt directories found at S3 path: {dir_path}")
    else:
        local_path = Path(dir_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Given TileDB-SOMA experiments directory path does not exist: {dir_path}")
        expt_uris = [str(p) for p in local_path.rglob("*") if p.name == "tiledbsoma_expt"]
        if not expt_uris:
            raise FileNotFoundError(f"No tiledbsoma_expt directories found in: {dir_path}")

    for expt_uri in expt_uris:
        with soma.Experiment.open(expt_uri) as expt:

            if is_s3_path(expt_uri):
                dataset = s3_name(s3_parent(expt_uri))
                batch = s3_name(s3_parent(expt_uri, levels=2))
            else:
                expt_path = Path(expt_uri)
                dataset = expt_path.parent.name
                batch = expt_path.parent.parent.name

            expt_name = batch + "_" + dataset

            obs_df = expt.obs.read(column_names=['donor_organism', 'dataset_workflow']).concat().to_pandas()

            # Check required routing columns are non-null
            skip = False
            for col in ['donor_organism', 'dataset_workflow']:
                if obs_df[col].isna().all():
                    print(f" - Skipping {expt_name}: '{col}' has all null values.")
                    skip = True
            if skip:
                continue

            # Check for mixed values within the dataset
            donor_organisms = obs_df['donor_organism'].dropna().unique()
            if len(donor_organisms) > 1:
                print(f" - Skipping {expt_name}: mixed donor_organism values: {list(donor_organisms)}.")
                continue

            dataset_workflows = obs_df['dataset_workflow'].dropna().unique()
            if len(dataset_workflows) > 1:
                print(f" - Skipping {expt_name}: mixed dataset_workflow values: {list(dataset_workflows)}.")
                continue

            donor_organism = donor_organisms[0].lower()
            dataset_workflow = dataset_workflows[0].lower()
            print(f"Batch: {batch}, Dataset: {dataset}, Donor Organism: {donor_organism}, Dataset Workflow: {dataset_workflow}")

            if donor_organism not in ORGANISM_COLLECTION_PREFIX:
                print(f" - Skipping {expt_name}: unrecognized donor_organism '{donor_organism}'.")
                continue
            organism_key = donor_organism

            # Map workflow → suffix
            workflow_map = {
                "smartseq": "ss2",
                "cellranger": "10x",
            }

            workflow_suffix = None
            for key, suffix in workflow_map.items():
                if key in dataset_workflow:
                    workflow_suffix = suffix
                    break

            if not workflow_suffix:
                print(f" - Skipping {expt_name}: unrecognized dataset_workflow '{dataset_workflow}' (expected 'cellranger' or 'smartseq2').")
                continue

            # Gene count check
            actual_genes = expt.ms["RNA"].var.count
            if workflow_suffix == "10x":
                expected_genes = CELLRANGER_EXPECTED_GENES[organism_key]
                if actual_genes != expected_genes:
                    print(f" - Skipping {expt_name}: gene count mismatch for {organism_key} cellranger dataset. Expected {expected_genes}, got {actual_genes}.")
                    continue
            elif workflow_suffix == "ss2":
                if dataset in SS2_DATASET_EXCEPTIONS:
                    expected_genes = SS2_DATASET_EXCEPTIONS[dataset]
                elif organism_key in SS2_EXPECTED_GENES:
                    expected_genes = SS2_EXPECTED_GENES[organism_key]
                else:
                    expected_genes = None
                if expected_genes is not None and actual_genes != expected_genes:
                    print(f" - Skipping {expt_name}: gene count mismatch for {organism_key} ss2 dataset. Expected {expected_genes}, got {actual_genes}.")
                    continue

            collection_name = f"{ORGANISM_COLLECTION_PREFIX[organism_key]}_{workflow_suffix}"

            if is_s3_path(collections_path):
                collection_uri = f"{collections_path}/{collection_name}"
            else:
                collection_uri = str(Path(collections_path) / collection_name)

            if not soma.Collection.exists(collection_uri):
                soma.Collection.create(collection_uri)
                print(f"Created new collection {collection_name} at path: {collection_uri}")

            with soma.Collection.open(collection_uri, "w") as coll:
                if expt_name in coll:
                    print(f" - Skipping {expt_name}: already exists in collection {collection_name}.")
                    continue

                # Var schema consistency check against existing experiments in the collection
                existing_keys = list(coll.keys())
                if existing_keys:
                    ref_var_columns = set(coll[existing_keys[0]].ms["RNA"].var.schema.names)
                    new_var_columns = set(expt.ms["RNA"].var.schema.names)
                    if ref_var_columns != new_var_columns:
                        missing = sorted(ref_var_columns - new_var_columns)
                        extra = sorted(new_var_columns - ref_var_columns)
                        msgs = []
                        if missing:
                            msgs.append(f"missing from new experiment: {missing}")
                        if extra:
                            msgs.append(f"extra in new experiment: {extra}")
                        print(f" - Skipping {expt_name}: var columns inconsistent with collection {collection_name} — {'; '.join(msgs)}.")
                        continue

                coll.set(expt_name, expt)
                print(f"Added experiment {expt_name} to collection {collection_name} at path: {collection_uri}")


if __name__ == "__main__":
    main()