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
from utils import is_s3_path, s3_parent, s3_name


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
    args = parser.parse_args()
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
        expt = soma.Experiment.open(expt_uri)

        if is_s3_path(expt_uri):
            dataset = s3_name(s3_parent(expt_uri))
            batch = s3_name(s3_parent(expt_uri, levels=2))
        else:
            expt_path = Path(expt_uri)
            dataset = expt_path.parent.name
            batch = expt_path.parent.parent.name

        donor_organism = expt.obs.read(column_names=['donor_organism']).concat().to_pandas()["donor_organism"].unique()[0].lower()
        dataset_workflow = expt.obs.read(column_names=['dataset_workflow']).concat().to_pandas()["dataset_workflow"].unique()[0].lower()
        print(f"Batch: {batch}, Dataset: {dataset}, Donor Organism: {donor_organism}, Dataset Workflow: {dataset_workflow}")

        expt_name = batch + "_" + dataset

        if donor_organism.lower() in ["human", "mouse"]:
            # Map workflow → suffix
            workflow_map = {
                "smartseq2": "ss2",
                "cellranger": "10x",
            }

            # Find matching workflow
            workflow_suffix = None
            for key, suffix in workflow_map.items():
                if key in dataset_workflow:
                    workflow_suffix = suffix
                    break

            if workflow_suffix:
                if donor_organism.lower() == "human":
                    collection_name = f"Human_{workflow_suffix}"
                else:
                    collection_name = f"Mouse_{workflow_suffix}"

                if is_s3_path(collections_path):
                    collection_uri = f"{collections_path}/{collection_name}"
                else:
                    collection_uri = str(Path(collections_path) / collection_name)

                with soma.Collection.open(collection_uri, "w") as coll:
                    coll.set(expt_name, expt)
                    print(f"Added experiment {expt_name} to collection {collection_name} at path: {collection_uri}")


if __name__ == "__main__":
    main()