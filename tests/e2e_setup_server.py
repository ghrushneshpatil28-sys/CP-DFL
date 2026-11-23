"""Empty, isolated database exclusively for browser first-run tests."""
import uuid
from backend.database import ROOT
from backend.main import create_app

directory = ROOT / ".test-tmp/e2e-setup" / uuid.uuid4().hex
directory.mkdir(parents=True)
app = create_app(f"sqlite:///{(directory / 'setup.db').as_posix()}", directory / "storage", allow_setup=True)
