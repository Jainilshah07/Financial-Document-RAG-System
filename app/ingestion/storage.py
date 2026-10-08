from pathlib import Path


class LocalFileStorage:
    """Keeps the original uploaded bytes on disk, named by content hash.

    Postgres stores only the path (`documents.storage_uri`), never the file. Naming by
    hash means the same bytes are stored once, and the raw file can always be re-parsed
    when the parser improves. Swappable later for an object store (S3, Azure Blob).
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def save(self, content_hash: str, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()[:10]  # keep the extension, bounded
        relative = Path(content_hash[:2]) / f"{content_hash}{suffix}"
        target = self._base_dir / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return relative.as_posix()

    def read(self, storage_uri: str) -> bytes:
        return (self._base_dir / storage_uri).read_bytes()
