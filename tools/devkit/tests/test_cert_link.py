"""./dev certify's latest-cert symlink: newest cert wins, link is relative,
re-linking replaces, and no certs means no link."""

import sys
import os
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cli  # noqa: E402


class CertLinkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "certs").mkdir()

    def _cert(self, name: str, mtime_offset: int = 0) -> Path:
        p = self.root / "certs" / name
        p.write_text('{"verdict": "PROMOTE_ELIGIBLE"}')
        if mtime_offset:
            st = p.stat()
            os.utime(p, (st.st_atime, st.st_mtime + mtime_offset))
        return p

    def test_no_certs_no_link(self):
        self.assertIsNone(cli.link_latest_cert(self.root))
        self.assertFalse(
            (self.root / "vercel-deploy" / "certs" / "latest.json").exists())

    def test_newest_cert_wins_and_link_is_relative(self):
        self._cert("docs-assist-100.cert.json")
        newest = self._cert("docs-assist-200.cert.json", mtime_offset=60)
        target = cli.link_latest_cert(self.root)
        self.assertEqual(target, newest)
        link = self.root / "vercel-deploy" / "certs" / "latest.json"
        self.assertTrue(link.is_symlink())
        self.assertFalse(Path(os.readlink(link)).is_absolute())
        self.assertEqual(link.resolve(), newest.resolve())

    def test_relink_replaces_existing_file(self):
        # the drop ships a regular latest.json — a passing run must replace it
        link = self.root / "vercel-deploy" / "certs" / "latest.json"
        link.parent.mkdir(parents=True)
        link.write_text('{"mock": true}')
        newest = self._cert("docs-assist-300.cert.json")
        cli.link_latest_cert(self.root)
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), newest.resolve())

    def test_custom_out_dir(self):
        (self.root / "demo-artifacts").mkdir()
        cert = self.root / "demo-artifacts" / "r.cert.json"
        cert.write_text("{}")
        target = cli.link_latest_cert(self.root, out_dir="demo-artifacts")
        self.assertEqual(target, cert)
        link = self.root / "vercel-deploy" / "certs" / "latest.json"
        self.assertEqual(link.resolve(), cert.resolve())


if __name__ == "__main__":
    unittest.main()
