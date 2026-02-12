#!/usr/bin/env python3

import argparse
from pathlib import Path
import scanpy as sc
import utils
import json
from copy import deepcopy


def main():
    parser = argparse.ArgumentParser(description="Compare schema/columns of current anndata object with a reference/previous anndata object.")
    parser.add_argument(
        "ref_schema", 
        type=str, 
        nargs='?',
        default='batch14_GSE76312',
        help="Name of the reference schema against which the current adata needs to be checked e.g., batch14_GSE76312. Default is batch14_GSE76312."
        )
    parser.add_argument(
        "h5ad_path", 
        type=Path, 
        help="Path to the annotated.h5ad file for which the schema needs to be checked."
        )
    args = parser.parse_args()
    ref_schema = Path("adata_schema_"+args.ref_schema+".json")
    ref_schema_path = Path(__file__).parent/"adata_schema_archive"/ref_schema
    h5ad_path = args.h5ad_path

    print(f"Reference schema: {ref_schema_path}")
    print(f"Current adata to be checked: {h5ad_path}")

    if not ref_schema_path.exists():
        raise FileNotFoundError(f"Reference schema not found: {ref_schema_path}")

    if not h5ad_path.exists():
        raise FileNotFoundError(f"annotated.h5ad file not found: {h5ad_path}")

    adata = sc.read_h5ad(h5ad_path)

    current_schema = utils.extract_adata_schema(adata)

    with ref_schema_path.open("r", encoding="utf-8") as f:
        ref_schema = json.load(f)

    if ref_schema['schema'] == current_schema['schema']:
        print("Schemas match (ignoring version)!")
    else:
        print("Schemas differ!")

        print(ref_schema['schema'])
        print(current_schema['schema'])


if __name__ == "__main__":
    main()