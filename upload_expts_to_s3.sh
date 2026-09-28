#!/usr/bin/env bash
# Upload TileDB-SOMA experiments to S3, skipping any dataset whose
# tiledbsoma_expt/ prefix already exists in the bucket.
#
# Usage:  ./upload_expts_to_s3.sh --group <scds|scrnalive> <batch> [batch ...]
#
# Examples:
#   ./upload_expts_to_s3.sh --group scds batch20
#   ./upload_expts_to_s3.sh --group scrnalive batch3 batch4
#   DRY_RUN=1 ./upload_expts_to_s3.sh --group scds batch20   # show what would happen
#
# --group is required: the two dataset groups live in different buckets and
# under different local roots, so defaulting either way risks writing to the
# wrong place.
set -u

DRY_RUN=${DRY_RUN:-0}
GROUP=""

while [ $# -gt 0 ]; do
    case "$1" in
        --group) GROUP=${2:-}; shift 2 ;;
        --group=*) GROUP=${1#*=}; shift ;;
        -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
        -*) echo "Unknown option: $1" >&2; exit 2 ;;
        *) break ;;
    esac
done

case "$GROUP" in
    scds)
        LOCAL_ROOT=/data/tiledb
        S3_ROOT=s3://rancho-scds-collections/tiledb-experiments
        ;;
    scrnalive)
        LOCAL_ROOT=/data/scrnalive_tiledb
        S3_ROOT=s3://rancho-scrna-live/tiledb-experiments
        ;;
    "")
        echo "Error: --group is required (scds or scrnalive)." >&2
        exit 2
        ;;
    *)
        echo "Error: unknown group '$GROUP' (expected scds or scrnalive)." >&2
        exit 2
        ;;
esac

if [ $# -eq 0 ]; then
    echo "Error: no batches given. Usage: $0 --group <scds|scrnalive> <batch> [batch ...]" >&2
    exit 2
fi

echo "Group:      $GROUP"
echo "Local root: $LOCAL_ROOT"
echo "S3 root:    $S3_ROOT"

for batch in "$@"; do
    if [ ! -d "$LOCAL_ROOT/$batch" ]; then
        echo "WARN  skipping $batch: $LOCAL_ROOT/$batch does not exist"
        continue
    fi

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
