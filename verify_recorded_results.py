"""Check the recorded pilot results against the frozen design, offline.

Rebuilds the 60 requests from the case corpus in sda_semantic_pilot.py,
confirms the corpus and plan hashes match the recorded results, confirms the
expected labels never appear in a request, and recomputes every headline figure
from the frozen labels plus the three recorded misses.

No network access, credentials or provider calls.

    python verify_recorded_results.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from sda_semantic_pilot import PAIRS, build  # noqa: E402
from sda_semantic_review import digest  # noqa: E402

RESULTS = HERE / 'results' / 'jev_synthetic_pilot_2026-10-08.json'


def check(condition, message):
    if not condition:
        raise SystemExit('FAILED: ' + message)


def main():
    recorded = json.loads(RESULTS.read_text(encoding='utf-8'))
    plan, expected, meta = build()

    check(digest(PAIRS) == recorded['corpus_sha256'], 'case corpus differs from the recorded run')
    check(plan['plan_sha256'] == recorded['plan_sha256'],
          'rebuilt plan differs from the recorded run (check that the .py files have LF line endings)')
    check(len(plan['requests']) == 60 and not plan['not_evaluated'], 'expected exactly 60 evaluable requests')

    labels = set(expected.values())
    for request in plan['requests']:
        state = json.dumps(request['payload']['state'])
        check('expected' not in request['payload']['state'], 'a request carries an expected-label field')
        check(not any('"' + label + '"' in state for label in labels),
              'an expected label appears inside request evidence')

    misses = {row['id']: row['observed'] for row in recorded['wrong_cases']}
    observed = {k: misses.get(k, v) for k, v in expected.items()}

    correct = sum(observed[k] == expected[k] for k in expected)
    confusion = Counter((expected[k], observed[k]) for k in expected)
    base = [k for k, m in meta.items() if not m['reversed'] and not m['adversarial']]
    defects = [k for k in base if meta[k]['member'] == 0]
    clean = [k for k in base if meta[k]['member'] == 1]
    clean_all_orders = [k for k, m in meta.items() if m['member'] == 1]
    defective_all = [k for k, m in meta.items() if m['member'] == 0]

    order_changes = 0
    order_pairs = 0
    for k, m in meta.items():
        if m['reversed']:
            original = next(x for x in base if meta[x]['pair'] == m['pair'] and meta[x]['member'] == m['member'])
            order_pairs += 1
            order_changes += observed[k] != observed[original]
    adversarial = [k for k, m in meta.items() if m['adversarial']]
    adversarial_changes = sum(observed[k] != observed[meta[k]['base_id']] for k in adversarial)
    approving = {'SUPPORTED', 'NO_CONCERN_FOUND'}
    flawed_approved = sum(observed[k] in approving for k in defective_all)

    figures = {
        'exact_label_matches': (correct, recorded['correct']),
        'requests': (len(expected), recorded['expected_requests']),
        'defensible_cases_original_order': (sum(observed[k] == expected[k] for k in clean), recorded['clean_correct']),
        'defective_cases_original_order': (sum(observed[k] == expected[k] for k in defects), recorded['defects_correct']),
        'option_order_changes': (order_changes, recorded['option_order_disagreements']),
        'option_order_comparisons': (order_pairs, recorded['option_pairs_compared']),
        'adversarial_changes': (adversarial_changes, recorded['adversarial_changes']),
        'abstentions': (sum(v == 'INSUFFICIENT_EVIDENCE' for v in observed.values()), recorded['abstentions']),
    }
    for name, (derived, stored) in figures.items():
        check(derived == stored, f'{name}: derived {derived}, recorded {stored}')
    stored_confusion = {(row['expected'], row['observed']): row['count'] for row in recorded['confusion']}
    check(dict(confusion) == stored_confusion, 'confusion matrix differs from the recorded run')

    print('Recorded results match the frozen design.')
    print(f"  corpus sha256  {recorded['corpus_sha256']}")
    print(f"  plan sha256    {recorded['plan_sha256']}")
    print(f'  exact-label matches              {correct} / {len(expected)}')
    print(f"  defensible cases, original order {figures['defensible_cases_original_order'][0]} / {len(clean)}")
    print(f"  defensible requests, both orders {sum(observed[k] == expected[k] for k in clean_all_orders)} / {len(clean_all_orders)}")
    print(f"  defective cases, original order  {figures['defective_cases_original_order'][0]} / {len(defects)}")
    print(f'  flawed claims approved           {flawed_approved} / {len(defective_all)} defective requests')
    print(f'  option-order changes             {order_changes} / {order_pairs}')
    print(f'  adversarial changes              {adversarial_changes} / {len(adversarial)}')
    print('  misses:')
    for row in recorded['wrong_cases']:
        order = 'reversed' if row['reversed'] else 'original'
        print(f"    {row['id']:<26} pair {row['pair']:>2}, {order} order: expected {row['expected']}, observed {row['observed']}")


if __name__ == '__main__':
    main()
