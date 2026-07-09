from pathlib import Path

_SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}
_SECRET_SUFFIXES = {".pem", ".key"}
_ALLOWED_SECRET_EXAMPLES = {".env.example", ".env.sample"}


class PathPolicy:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def ensure_inside_project(self, path: str) -> Path:
        candidate = (self.project_root / path).resolve()
        if self.project_root not in candidate.parents and candidate != self.project_root:
            raise PermissionError(f"Path is outside project root: {path}")
        name = candidate.name
        if name not in _ALLOWED_SECRET_EXAMPLES and (
            name in _SECRET_NAMES or any(name.endswith(suffix) for suffix in _SECRET_SUFFIXES)
        ):
            raise PermissionError(f"Refusing to access secret-like file: {path}")
        if ".git" in candidate.parts and candidate.name != ".gitignore":
            raise PermissionError(f"Refusing to access .git internals: {path}")
        return candidate
