#!/usr/bin/env bash
# Run tiledbsoma_experiment.py on only the batch3 datasets that don't yet have
# a TileDB-SOMA experiment in /data/scrnalive_tiledb/batch3/.
set -u

SRC=/data/scrnalive_complete/batch3
OUT=/data/scrnalive_tiledb
LOGDIR=$OUT/batch3_logs
mkdir -p "$LOGDIR"

for ds_dir in "$SRC"/*/; do
    ds=$(basename "$ds_dir")
    expt="$OUT/batch3/$ds/tiledbsoma_expt"

    if [ -d "$expt" ]; then
        echo "SKIP  $ds (already at $expt)"
        continue
    fi

    if ! find "$ds_dir" -name "*annotated.h5ad" | grep -q .; then
        echo "SKIP  $ds (no annotated.h5ad)"
        continue
    fi

    echo "RUN   $ds  ($(date '+%F %T'))"
    python tiledbsoma_experiment.py "$ds_dir" \
        --dataset-group scrnalive \
        --output "$OUT" \
        --log-file "$LOGDIR/${ds}_experiment.log"

    if [ $? -eq 0 ] && [ -d "$expt" ]; then
        echo "OK    $ds  ($(date '+%F %T'))"
    else
        echo "FAIL  $ds  ($(date '+%F %T')) - see $LOGDIR/${ds}_experiment.log"
    fi
done

echo "DONE  ($(date '+%F %T'))"
