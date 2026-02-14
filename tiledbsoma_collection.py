#!/usr/bin/env python3



import argparse
from pathlib import Path
import tiledbsoma as soma


def main():

    parser = argparse.ArgumentParser(description="Add TileDB-SOMA experiment to the appropriate collection (Human_10x/Human_ss2/Mouse_10x/Mouse_ss2).")
    parser.add_argument(
        "expt_path", 
        type=Path, 
        help="Path to the TileDB-SOMA experiment that needs to be added to the collection"
        )
    args = parser.parse_args()
    expt_path = args.expt_path
    print(f"Given TileDB-SOMA experiment path: {expt_path}")

    if not expt_path.exists():
        raise FileNotFoundError(f"Given TileDB-SOMA experiment path does not exist: {expt_path}")
    
    expt = soma.Experiment.open(str(expt_path))
    
    dataset = expt_path.parent.name
    batch = expt_path.parent.parent.name
    donor_organism = expt.obs.read(column_names=['donor_organism']).concat().to_pandas()["donor_organism"].unique()[0].lower()
    dataset_workflow = expt.obs.read(column_names=['dataset_workflow']).concat().to_pandas()["dataset_workflow"].unique()[0].lower()
    print(f"Batch: {batch}, Dataset: {dataset}, Donor Organism: {donor_organism}, Dataset Workflow: {dataset_workflow}")

    collections_path = Path("/wip/scds/delivery-zips/tiledbsoma_collections/")
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