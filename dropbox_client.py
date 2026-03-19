"""
Step 1 & 2 of the workflow — Dropbox integration.

1. List all files/subfolders in a Dropbox folder.
2. Download the most recent file.
"""

import os
import tempfile

import dropbox

from config import DROPBOX_ACCESS_TOKEN, DROPBOX_FOLDER_PATH


def get_dropbox_client() -> dropbox.Dropbox:
    """Return an authenticated Dropbox client."""
    if not DROPBOX_ACCESS_TOKEN:
        raise ValueError("DROPBOX_ACCESS_TOKEN is not set in your .env file.")
    return dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)


def list_files(folder_path: str = DROPBOX_FOLDER_PATH) -> list[dropbox.files.FileMetadata]:
    """List all files in the given Dropbox folder, sorted newest-first."""
    dbx = get_dropbox_client()
    result = dbx.files_list_folder(folder_path)
    files = [
        entry
        for entry in result.entries
        if isinstance(entry, dropbox.files.FileMetadata)
    ]
    # Sort by last modified (newest first)
    files.sort(key=lambda f: f.server_modified, reverse=True)
    return files


def download_latest_file(folder_path: str = DROPBOX_FOLDER_PATH) -> tuple[str, str]:
    """
    Download the most recently modified file from the Dropbox folder.

    Returns:
        (local_file_path, original_filename)
    """
    files = list_files(folder_path)
    if not files:
        raise FileNotFoundError(f"No files found in Dropbox folder: {folder_path}")

    latest = files[0]
    print(f"[Dropbox] Downloading: {latest.name}  (modified {latest.server_modified})")

    dbx = get_dropbox_client()
    _, response = dbx.files_download(latest.path_lower)

    # Save to a temp file preserving the extension
    ext = os.path.splitext(latest.name)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(response.content)
    tmp.close()

    return tmp.name, latest.name
