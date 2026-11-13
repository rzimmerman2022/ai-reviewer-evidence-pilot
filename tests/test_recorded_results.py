"""The recorded results must stay consistent with the frozen design."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_recorded_results_match_frozen_design():
    run = subprocess.run([sys.executable, str(ROOT / 'verify_recorded_results.py')],
                         capture_output=True, text=True, cwd=ROOT)
    assert run.returncode == 0, run.stdout + run.stderr
    assert 'exact-label matches              57 / 60' in run.stdout
    assert 'flawed claims approved           0 / 32' in run.stdout
    readme = (ROOT / 'README.md').read_text(encoding='utf-8').lower()
    assert 'does not establish' not in readme
    assert 'small constructed test set' not in readme
