"""Temporary authoring roots shared by validation and license tests."""
import contextlib
import pathlib
import shutil
import tempfile
from unittest.mock import patch

import authoring


@contextlib.contextmanager
def fixture_root(*folders):
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp)
        for folder in folders:
            shutil.copytree(authoring.ROOT / folder, root / folder)
        shutil.copyfile(authoring.ROOT / "index.json", root / "index.json")
        with patch.object(authoring, "ROOT", root):
            yield root
