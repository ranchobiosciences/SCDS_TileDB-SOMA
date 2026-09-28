#!/usr/bin/env python3
"""
rewrite_collection_uris.py

Repoint synced TileDB-SOMA collections at your own bucket, in one command.

    python rewrite_collection_uris.py s3://your-bucket --apply

That discovers every collection under `s3://your-bucket/collections/`, rewrites
each member URI from `s3://rancho-scrna-live` to `s3://your-bucket`, and
verifies the new targets exist first. Drop `--apply` for a dry run.

Why this is needed
------------------
A SOMA collection stores each member as an ABSOLUTE URI, because the experiments
live in a sibling prefix (`tiledb-experiments/`) rather than inside the
collection's own prefix. TileDB only stores a relative member path when the
member sits under the group, and a relative `../` path does not resolve, so a
collection copied to another bucket still points at the source bucket.

That failure is silent while you still hold credentials to the source: queries
appear to work but stream from the original bucket, so you get no egress saving
and no isolation. It becomes `DoesNotExistError` the day that access ends.

Experiments and manifests need no fix-up. Experiments store their internal
members relatively and relocate cleanly; manifests hold no URIs at all, only
`batch`, `curation_dataset_id`, `experiment`, and `collection_name` tags.

Run this AFTER `aws s3 sync` of `tiledb-experiments/`, so the targets exist.

Other forms
-----------
    # dry run (default)
    python rewrite_collection_uris.py s3://your-bucket

    # one collection only
    python rewrite_collection_uris.py s3://your-bucket/collections/Human_10x --apply

    # a local mirror
    python rewrite_collection_uris.py /mnt/scrna-live --apply

    # non-default source prefix
    python rewrite_collection_uris.py s3://your-bucket --old-prefix s3://old-bucket --apply
"""
import argparse
import sys
from pathlib import Path

import tiledb
import tiledbsoma as soma

DEFAULT_OLD_PREFIX = "s3://rancho-scrna-live"


def is_s3(p):
    return str(p).startswith("s3://")


def _s3fs():
    import s3fs
    return s3fs.S3FileSystem()


def list_children(prefix):
    """Immediate child directory names under prefix."""
    if is_s3(prefix):
        fs = _s3fs()
        out = []
        for entry in fs.ls(prefix[5:].rstrip("/") + "/", detail=True):
            if entry.get("type") == "directory":
                out.append(entry["name"].rstrip("/").split("/")[-1])
        return sorted(out)
    return sorted(c.name for c in Path(prefix).iterdir() if c.is_dir())


def exists(uri):
    if is_s3(uri):
        return _s3fs().exists(uri[5:].rstrip("/"))
    return Path(uri).exists()


def join(base, *parts):
    base = str(base).rstrip("/")
    return base + "/" + "/".join(str(p).strip("/") for p in parts)


def resolve_targets(target):
    """Return (new_prefix, [collection_uri, ...]) from whatever the user passed."""
    t = str(target).rstrip("/")

    # a single collection: it is a TileDB group
    if exists(join(t, "__group")) or soma.Collection.exists(t):
        # new prefix is the root two levels up: <root>/collections/<Name>
        root = t.rsplit("/", 2)[0]
        return root, [t]

    # the collections directory itself
    if t.endswith("/collections") or Path(t).name == "collections":
        root = t.rsplit("/", 1)[0]
        return root, [join(t, c) for c in list_children(t)]

    # a bucket or mirror root
    coll_dir = join(t, "collections")
    if exists(coll_dir):
        return t, [join(coll_dir, c) for c in list_children(coll_dir)]

    sys.exit(f"Could not find a collection, a collections/ directory, or "
             f"{coll_dir} under: {target}")


def stored_members(collection_uri):
    """{name: stored_uri} exactly as recorded in the group, not as resolved."""
    with soma.Collection.open(collection_uri) as coll:
        return {name: value[0] for name, value in coll.members().items()}


def normalize(uri):
    """Group members come back as file:// for local paths; S3 URIs are unchanged."""
    return uri[7:] if uri.startswith("file://") else uri


def rewrite_one(collection_uri, old, new, apply_, skip_verify):
    """Returns (n_rewritten, n_already, n_unmatched, n_missing)."""
    name_short = collection_uri.rstrip("/").split("/")[-1]
    members = stored_members(collection_uri)
    if not members:
        print(f"  {name_short}: no members, skipping")
        return 0, 0, 0, 0

    plan, already, unmatched = {}, [], []
    for key, raw in members.items():
        uri = normalize(raw)
        if uri.startswith(new):
            already.append(key)
        elif uri.startswith(old):
            plan[key] = new + uri[len(old):]
        else:
            unmatched.append((key, uri))

    status = f"  {name_short}: {len(members)} members, {len(plan)} to rewrite"
    if already:
        status += f", {len(already)} already correct"
    if unmatched:
        status += f", {len(unmatched)} UNMATCHED"
    print(status)
    for key, uri in unmatched[:3]:
        print(f"      unmatched: {key} -> {uri}")

    if not plan:
        return 0, len(already), len(unmatched), 0

    missing = []
    if not skip_verify:
        missing = [k for k, u in plan.items() if not exists(u)]
        if missing:
            print(f"      {len(missing)} target(s) NOT found, skipping this collection. "
                  f"Sync tiledb-experiments/ first, or pass --skip-verify.")
            for k in missing[:3]:
                print(f"        {k} -> {plan[k]}")
            return 0, len(already), len(unmatched), len(missing)

    if not apply_:
        ex = next(iter(plan.items()))
        print(f"      e.g. {ex[0]}")
        print(f"           {normalize(members[ex[0]])}")
        print(f"        -> {ex[1]}")
        return len(plan), len(already), len(unmatched), 0

    # TileDB will not remove and re-add the same member name inside one write
    # transaction, so each step opens the group on its own.
    for key in plan:
        with tiledb.Group(collection_uri, "w") as g:
            g.remove(key)
    for key, uri in plan.items():
        with tiledb.Group(collection_uri, "w") as g:
            g.add(uri=uri, name=key)

    after = {k: normalize(u) for k, u in stored_members(collection_uri).items()}
    bad = [k for k, u in after.items() if not u.startswith(new)]
    if bad:
        print(f"      WARNING: {len(bad)} member(s) still outside {new}: {bad[:3]}")
    else:
        print(f"      rewrote {len(plan)}, all {len(after)} now resolve under {new}")
    return len(plan), len(already), len(unmatched), 0


def main():
    ap = argparse.ArgumentParser(
        description="Repoint synced TileDB-SOMA collections at your own bucket.")
    ap.add_argument("target", help="Your bucket root, e.g. s3://your-bucket. Also accepts a "
                                   "collections/ directory or a single collection URI.")
    ap.add_argument("--old-prefix", default=DEFAULT_OLD_PREFIX,
                    help=f"Prefix to replace. Default {DEFAULT_OLD_PREFIX}")
    ap.add_argument("--new-prefix", default=None,
                    help="Replacement prefix. Defaults to the target root.")
    ap.add_argument("--apply", action="store_true",
                    help="Actually write. Without this the script only reports.")
    ap.add_argument("--skip-verify", action="store_true",
                    help="Do not check that each new target exists before writing.")
    args = ap.parse_args()

    old = args.old_prefix.rstrip("/")
    root, collections = resolve_targets(args.target)
    new = (args.new_prefix or root).rstrip("/")

    print(f"target root : {root}")
    print(f"rewriting   : {old}  ->  {new}")
    print(f"collections : {len(collections)} found")
    if old == new:
        sys.exit("old and new prefixes are identical, nothing to do")

    tot = [0, 0, 0, 0]
    for uri in collections:
        r, a, u, m = rewrite_one(uri, old, new, args.apply, args.skip_verify)
        tot = [tot[0] + r, tot[1] + a, tot[2] + u, tot[3] + m]

    verb = "rewrote" if args.apply else "would rewrite"
    print(f"\n{verb} {tot[0]} member(s) across {len(collections)} collection(s); "
          f"{tot[1]} already correct, {tot[2]} unmatched, {tot[3]} missing target(s)")
    if not args.apply and tot[0]:
        print("Dry run. Re-run with --apply to write.")
    if tot[2] or tot[3]:
        sys.exit(1)


if __name__ == "__main__":
    main()
