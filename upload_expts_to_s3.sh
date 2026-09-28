#!/usr/bin/env bash
# Upload TileDB-SOMA experiments to S3, skipping any dataset whose
# tiledbsoma_expt/ prefix already exists in the bucket.
#
# Usage:  ./upload_expts_to_s3.sh batch4 [batch3 ...]
#         DRY_RUN=1 ./upload_expts_to_s3.sh batch4    # show what would happen
set -u

LOCAL_ROOT=/data/scrnalive_tiledb
S3_ROOT=s3://rancho-scrna-live/tiledb-experiments
DRY_RUN=${DRY_RUN:-0}

for batch in "$@"; do
    logdir=$LOCAL_ROOT/${batch}_upload_logs
    mkdir -p "$logdir"
    echo "########## $batch ($(date '+%F %T')) ##########"

    for expt in "$LOCAL_ROOT/$batch"/*/tiledbsoma_expt; do
        [ -d "$expt" ] || continue
        ds=$(basename "$(dirname "$expt")")
        dest="$S3_ROOT/$batch/$ds/tiledbsoma_expt"

        # Already on S3? (any object under the tiledbsoma_expt/ prefix)
        if aws s3 ls "$dest/" --recursive 2>/dev/null | grep -q .; then
            echo "SKIP  $ds (already at $dest/)"
            continue
        fi

        size=$(du -sh "$expt" | cut -f1)
        if [ "$DRY_RUN" = "1" ]; then
            echo "WOULD $ds ($size) -> $dest/"
            continue
        fi

        echo "PUSH  $ds ($size)  ($(date '+%F %T'))"
        aws s3 sync "$expt/" "$dest/" --only-show-errors \
            > "$logdir/${ds}_upload.log" 2>&1
        rc=$?

        # Verify: local file count should match remote object count.
        n_local=$(find "$expt" -type f | wc -l)
        n_s3=$(aws s3 ls "$dest/" --recursive 2>/dev/null | grep -c .)
        if [ $rc -eq 0 ] && [ "$n_local" -eq "$n_s3" ]; then
            echo "OK    $ds ($n_s3 objects)  ($(date '+%F %T'))"
        else
            echo "FAIL  $ds (rc=$rc local=$n_local s3=$n_s3) - see $logdir/${ds}_upload.log"
        fi
    done
done

echo "DONE  ($(date '+%F %T'))"
