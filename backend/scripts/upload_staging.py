"""Upload staged parquet tables to S3-compatible object storage (Cloudflare R2).

Ingestion runs on a workstation; the deployed API reads the same parquet over HTTP
via DuckDB's httpfs. This script moves the staging folder into a bucket.

Size check first (no credentials needed, no upload):

    python -m scripts.upload_staging --dry-run

Upload (credentials from the environment or a .env in backend/):

    set S3_ACCESS_KEY_ID=...
    set S3_SECRET_ACCESS_KEY=...
    set R2_ACCOUNT_ID=...
    python -m scripts.upload_staging --bucket datasport-vault --prefix staging

Requires boto3 for the upload path only:  pip install boto3
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Executer.duckdb_store import STAGING_VIEWS, default_staging_dir  # noqa: E402

# R2's free allowance, for the dry-run verdict.
FREE_TIER_GB = 10.0


def _human(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:,.1f} {unit}"
        value /= 1024
    return f"{value:,.1f} TB"


def staged_files(staging_dir: Path) -> list[Path]:
    """Parquet files for known staging views, largest last."""
    found = []
    for stem in STAGING_VIEWS:
        path = staging_dir / f"{stem}.parquet"
        if path.exists() and path.stat().st_size > 0:
            found.append(path)
    return sorted(found, key=lambda p: p.stat().st_size)


def report(files: list[Path], staging_dir: Path) -> int:
    total = sum(p.stat().st_size for p in files)
    print(f"Staging directory: {staging_dir}")
    print(f"Tables found: {len(files)} of {len(STAGING_VIEWS)}\n")

    width = max((len(p.stem) for p in files), default=10)
    for path in files:
        print(f"  {path.stem.ljust(width)}  {_human(path.stat().st_size).rjust(10)}")

    print(f"\n  {'TOTAL'.ljust(width)}  {_human(total).rjust(10)}")

    missing = [s for s in STAGING_VIEWS if not (staging_dir / f"{s}.parquet").exists()]
    if missing:
        print(f"\nNot staged yet: {', '.join(missing)}")

    # Parquet sitting in staging that no view claims. These are not uploaded, so a
    # table added to ingestion but not to STAGING_VIEWS would otherwise reach
    # production as an empty feature with nothing in the logs to say why.
    unregistered = sorted(
        path for path in staging_dir.glob("*.parquet") if path.stem not in STAGING_VIEWS
    )
    if unregistered:
        skipped = sum(path.stat().st_size for path in unregistered)
        print(f"\nIn staging but not in STAGING_VIEWS, so NOT uploaded ({_human(skipped)}):")
        for path in unregistered:
            print(f"  {path.stem}  ({_human(path.stat().st_size)})")
        print("  Add the stem to STAGING_VIEWS if the deployed API should read it.")

    total_gb = total / (1024**3)
    print(f"\nCloudflare R2 free tier is {FREE_TIER_GB:g} GB.")
    if total_gb <= FREE_TIER_GB:
        headroom = FREE_TIER_GB - total_gb
        print(f"  Fits, with {headroom:.1f} GB to spare.")
    else:
        print(f"  Over by {total_gb - FREE_TIER_GB:.1f} GB — trim before uploading.")
        print("  Largest tables are listed last above; dropping or narrowing the")
        print("  season range on those is usually the cheapest fix.")
    return total


def upload(files: list[Path], bucket: str, prefix: str) -> None:
    try:
        import boto3
    except ImportError:
        sys.exit("boto3 is required for uploads: pip install boto3")

    key_id = os.getenv("S3_ACCESS_KEY_ID", "").strip()
    secret = os.getenv("S3_SECRET_ACCESS_KEY", "").strip()
    if not (key_id and secret):
        sys.exit("Set S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY.")

    account_id = os.getenv("R2_ACCOUNT_ID", "").strip()
    endpoint = os.getenv("S3_ENDPOINT", "").strip()
    if account_id and not endpoint:
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    if not endpoint:
        sys.exit("Set R2_ACCOUNT_ID (for R2) or S3_ENDPOINT (for other providers).")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name=os.getenv("S3_REGION", "auto"),
    )

    prefix = prefix.strip("/")
    for path in files:
        key = f"{prefix}/{path.name}" if prefix else path.name
        size = _human(path.stat().st_size)
        print(f"  uploading {path.name} ({size}) -> s3://{bucket}/{key}")
        client.upload_file(str(path), bucket, key)

    print(f"\nDone. Point the API at it:\n  STAGING_DATA_URI=r2://{bucket}/{prefix}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", help="Destination bucket name")
    parser.add_argument("--prefix", default="staging", help="Key prefix (default: staging)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report table sizes and the free-tier verdict without uploading",
    )
    args = parser.parse_args()

    staging_dir = default_staging_dir()
    if not staging_dir.is_dir():
        sys.exit(f"Staging directory not found: {staging_dir}")

    files = staged_files(staging_dir)
    if not files:
        sys.exit(f"No staged parquet files in {staging_dir}")

    report(files, staging_dir)

    if args.dry_run:
        return
    if not args.bucket:
        sys.exit("\n--bucket is required to upload (or pass --dry-run).")

    print()
    upload(files, args.bucket, args.prefix)


if __name__ == "__main__":
    main()
