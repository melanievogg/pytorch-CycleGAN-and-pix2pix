"""Standard-library integration checks for the standalone viewer."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'build_cyclegan_viewer.py'
spec = importlib.util.spec_from_file_location('viewer', SCRIPT)
viewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(viewer)


class ViewerTests(unittest.TestCase):
    def test_cli_reports_copies_and_safe_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'
            output = Path(tmp) / 'viewer'
            root.mkdir()
            for base, kinds in [('subject010_OS_bscan_0002', viewer.KINDS),
                                ('subject002_OD_bscan_0010', ('real_A',))]:
                for kind in kinds:
                    (root / f'{base}_{kind}.png').write_bytes(b'unchanged source bytes')
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = subprocess.run([sys.executable, str(SCRIPT), '--results-dir', str(root),
                                     '--output-dir', str(output), '--title', '<QC>'],
                                    capture_output=True, text=True, check=True)
            self.assertIn('Vollständige Achtergruppen: 1', result.stdout)
            with (output / 'viewer_manifest.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([r['subject'] for r in rows], ['002', '010'])
            self.assertEqual([r['complete_group'] for r in rows], ['False', 'True'])
            with (output / 'missing_files.csv').open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 7)
            page = (output / 'index.html').read_text()
            self.assertIn('<title>&lt;QC&gt;</title>', page)
            payload = page.split('<script id="data" type="application/json">')[1].split('</script>')[0]
            data = json.loads(payload)
            self.assertEqual(data['kinds'], list(viewer.KINDS))
            for case in data['cases']:
                for relative in case['images'].values():
                    self.assertEqual((output / relative).read_bytes(), b'unchanged source bytes')
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_recursive_collisions_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for parent in ('one', 'two'):
                (root / parent).mkdir()
                (root / parent / 'scan2_real_A.png').touch()
            groups = viewer.group_images(viewer.find_result_images(root, True), root)
            self.assertEqual([g['id'] for g in groups], ['one/scan2', 'two/scan2'])
            (root / 'one' / 'scan2_real_A.jpg').touch()
            with self.assertRaisesRegex(ValueError, 'Ambiguous duplicate'):
                viewer.group_images(viewer.find_result_images(root, True), root)

    def test_names_and_fallback_order(self):
        self.assertEqual(viewer.extract_basename(Path('long_fake_B_name_real_A.PNG')),
                         ('long_fake_B_name', 'real_A'))
        self.assertIsNone(viewer.extract_basename(Path('unrelated.png')))
        self.assertEqual(viewer.parse_metadata('arbitrary_name'), {})
        self.assertEqual(sorted(['scan10', 'scan2'], key=viewer.natural_key), ['scan2', 'scan10'])


if __name__ == '__main__':
    unittest.main()
