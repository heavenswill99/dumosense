import contextlib,io,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from mvp_pipeline import run_pipeline

class FailureLifecycleTests(unittest.TestCase):
    def test_missing_input_fails_and_preserves_latest_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);pointer=root/'latest_successful_run.json'
            pointer.write_text('{"run_id":"previous-good"}',encoding='utf-8')
            args=SimpleNamespace(data_dir=str(root/'missing'),validation_dir=str(root/'missing'),output_dir=str(root))
            # Isolate failure handling: the nested test subprocess is outside this fixture.
            with patch('mvp_pipeline.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')), contextlib.redirect_stdout(io.StringIO()):
                code=run_pipeline(args)
            self.assertEqual(code,1)
            self.assertEqual(json.loads(pointer.read_text())['run_id'],'previous-good')
            manifests=list((root/'runs').glob('*/manifest.json'))
            self.assertEqual(len(manifests),1)
            self.assertEqual(json.loads(manifests[0].read_text())['status'],'failed')
            self.assertIn('FAILED',(manifests[0].parent/'execution_log.txt').read_text())
