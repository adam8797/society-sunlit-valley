#!/usr/bin/env python3
"""
Unzip GameNight-3.0.0.zip, load manifest.json, let you modify it programmatically,
then re-zip contents back to the same zip file.

- Edit the `modify_manifest(manifest: dict) -> dict` function below to implement your changes.
- Or provide a separate modifier module using --modifier /path/to/modifier.py which must
  export a function `modify_manifest(manifest: dict) -> dict`.
"""

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional

DEFAULT_ZIP = Path("./build/curseforge/GameNight-3.0.0.zip")
PROJECTS_TO_REMOVE = [890127,889079,406463]
BACKUP_SUFFIX = ".bak"


def rezip_directory(src_dir: Path, dst_zip: Path) -> None:
    """Recreate a zip from directory contents, preserving relative paths."""
    compression = zipfile.ZIP_DEFLATED if hasattr(zipfile, "ZIP_DEFLATED") else zipfile.ZIP_STORED
    with zipfile.ZipFile(dst_zip, "w", compression=compression) as zf:
        for root, dirs, files in os.walk(src_dir):
            rootp = Path(root)
            for file in files:
                fpath = rootp / file
                arcname = fpath.relative_to(src_dir)
                zf.write(fpath, arcname.as_posix())


def modify_manifest(manifest: dict) -> dict:

    for file in manifest["files"]:
        if file.get("projectID") in PROJECTS_TO_REMOVE:
            print(f"Removing projectID {file['projectID']} from manifest")
            manifest["files"].remove(file)

    return manifest


def main():
    zip_path = DEFAULT_ZIP
    if not zip_path.exists():
        print(f"Zip file not found: {zip_path}", file=sys.stderr)
        sys.exit(1)

    # Temporary extraction
    with tempfile.TemporaryDirectory(prefix="fix-curseforge-") as tmpdir:
        tmpdir_path = Path(tmpdir)
        print(f"Extracting {zip_path} to temporary folder {tmpdir_path} ...")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)
        except zipfile.BadZipFile as e:
            print(f"Bad zip file: {e}", file=sys.stderr)
            sys.exit(3)

        manifest_path = tmpdir_path / "manifest.json"
        try:
            with manifest_path.open("r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        except Exception as e:
            print(f"Error reading manifest JSON: {e}", file=sys.stderr)
            sys.exit(5)

        modify_manifest(manifest)

        # Validate JSON serializable
        try:
            json_str = json.dumps(manifest, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Modified manifest is not JSON serializable: {e}", file=sys.stderr)
            sys.exit(8)

        # Write modified manifest back
        try:
            with manifest_path.open("w", encoding="utf-8") as fh:
                fh.write(json_str)
                fh.write("\n")
        except Exception as e:
            print(f"Error saving manifest: {e}", file=sys.stderr)
            sys.exit(9)

        # Create new zip in same directory and move over original
        new_zip_path = zip_path.with_suffix(zip_path.suffix + ".new")
        print(f"Creating new zip at {new_zip_path} ...")
        try:
            rezip_directory(tmpdir_path, new_zip_path)
        except Exception as e:
            print(f"Failed to create new zip: {e}", file=sys.stderr)
            sys.exit(11)

        print(f"Replacing original zip {zip_path} with updated zip {new_zip_path} ...")
        try:
            # Move new zip into place atomically where possible
            os.replace(str(new_zip_path), str(zip_path))
        except Exception as e:
            print(f"Failed to replace original zip: {e}", file=sys.stderr)
            sys.exit(12)

        print("Done. Updated zip saved.")


if __name__ == "__main__":
    main()