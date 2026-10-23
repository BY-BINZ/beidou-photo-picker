import json
from pathlib import Path
import tempfile
import unittest

from picking.core import export_files, match_files


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.small, self.large, self.out = (self.root / name for name in ('selected', 'originals', 'output'))
        self.small.mkdir()
        self.large.mkdir()

    def write(self, root, name, content=b'fixture'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_structure_duplicate_and_no_overwrite(self):
        self.write(self.small, '商家/款号/BR5_7539.jpg')
        self.write(self.small, '商家/款号/BR5_7539 - 副本.jpg')
        self.write(self.large, 'BR5_7539.cr3', b'original payload')
        existing = self.write(self.out, '商家/款号/BR5_7539.cr3', b'do not overwrite')
        result = export_files(match_files(self.small, self.large), self.out)
        self.assertEqual(result['copied'], 2)
        self.assertEqual(existing.read_bytes(), b'do not overwrite')
        self.assertEqual((existing.parent / 'BR5_7539_1.cr3').read_bytes(), b'original payload')
        self.assertEqual((existing.parent / 'BR5_7539 - 副本.cr3').read_bytes(), b'original payload')
        records = [json.loads(line) for line in Path(result['log']).read_text(encoding='utf-8').splitlines()]
        self.assertEqual(sum(r['event'] == 'copied' for r in records), 2)
        self.assertTrue(all('sha256' in r for r in records if r['event'] == 'copied'))

    def test_short_camera_number_never_matches(self):
        self.write(self.small, 'BR5_7539.jpg')
        self.write(self.large, 'BR5_7543.cr3')
        self.assertEqual(match_files(self.small, self.large).rows[0].status, 'missing')

    def test_ambiguous_number_does_not_pick_first(self):
        self.write(self.small, 'selected_7539.jpg')
        self.write(self.large, 'cameraA_7539.cr3')
        self.write(self.large, 'cameraB_7539.nef')
        plan = match_files(self.small, self.large)
        self.assertEqual(plan.rows[0].status, 'ambiguous')
        result = export_files(plan, self.out)
        self.assertEqual((result['copied'], result['unresolved']), (0, 1))

    def test_same_merchant_has_priority(self):
        self.write(self.small, '商家A/BR5_7539.jpg')
        wanted = self.write(self.large, '商家A/BR5_7539.cr3')
        self.write(self.large, '商家B/BR5_7539.cr3')
        self.assertEqual(match_files(self.small, self.large).rows[0].original, str(wanted.resolve()))

    def test_missing_source_is_recorded_and_other_files_continue(self):
        self.write(self.small, '0001.jpg')
        self.write(self.small, '0002.jpg')
        removed = self.write(self.large, '0001.cr3')
        kept = self.write(self.large, '0002.cr3')
        plan = match_files(self.small, self.large)
        removed.unlink()
        result = export_files(plan, self.out)
        self.assertEqual((result['copied'], result['failed']), (1, 1))
        self.assertTrue(kept.exists())
        self.assertFalse(list(self.out.glob('.picking-*.part')))

    def test_nested_output_and_input_are_rejected(self):
        plan = match_files(self.small, self.large)
        with self.assertRaises(ValueError):
            export_files(plan, self.small / 'export')
        with self.assertRaises(ValueError):
            match_files(self.small, self.small)

    def test_jpg_and_raw_with_same_name_require_review(self):
        self.write(self.small, '0001.jpg')
        self.write(self.large, '0001.jpg')
        self.write(self.large, '0001.cr3')
        self.assertEqual(match_files(self.small, self.large).rows[0].status, 'ambiguous')


if __name__ == '__main__':
    unittest.main()
