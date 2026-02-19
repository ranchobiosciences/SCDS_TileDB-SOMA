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


def main():

    parser = argparse.ArgumentParser(description="Add TileDB-SOMA experiments to the appropriate collection (Human_10x/Human_ss2/Mouse_10x/Mouse_ss2).")
    parser.add_argument(
        "dir_path", 
        type=Path, 
        help="Path to the directory with TileDB-SOMA experiments that needs to be added to the collection."
    )
    args = parser.parse_args()
    dir_path = args.dir_path
    print(f"Given TileDB-SOMA experiments directory path: {dir_path}")

    if not dir_path.exists():
        raise FileNotFoundError(f"Given TileDB-SOMA experiments directory path does not exist: {dir_path}")

    collections_path = Path("/wip/scds/delivery-zips/tiledbsoma_collections/")

    for expt_path in dir_path.rglob("*"):
        if expt_path.name == "tiledbsoma_expt":
            expt = soma.Experiment.open(str(expt_path))        
            dataset = expt_path.parent.name
            batch = expt_path.parent.parent.name
            donor_organism = expt.obs.read(column_names=['donor_organism']).concat().to_pandas()["donor_organism"].unique()[0].lower()
            dataset_workflow = expt.obs.read(column_names=['dataset_workflow']).concat().to_pandas()["dataset_workflow"].unique()[0].lower()
            print(f"Batch: {batch}, Dataset: {dataset}, Donor Organism: {donor_organism}, Dataset Workflow: {dataset_workflow}")

            expt_name = batch+"_"+dataset

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
                    collection_path = collections_path / collection_name

                    with soma.Collection.open(str(collection_path), "w") as coll:
                        coll.set(expt_name, expt)
                        print(f"Added experiment {expt_name} to collection {collection_name} at path: {collection_path}")


if __name__ == "__main__":
    main()