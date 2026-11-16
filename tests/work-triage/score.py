#!/usr/bin/env python3
"""Parse and score work-triage plans using only the standard library."""
from __future__ import annotations

import argparse
import json
import re
from posixpath import normpath
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
COLUMNS = ['#', 'Row', 'Model', 'Level', 'Run as', 'Starts after', 'Owns', 'Check', 'Escalate if']
MODELS = {'Sonnet 5.5', 'Opus 5.5', 'Fable 5.2', 'gpt-6.1-sol', 'gpt-6-luna', 'gpt-6-astra', 'gpt-6.1-terra'}
LEVELS = {'low', 'medium', 'high', 'xhigh'}
RUN_AS = {'subagent', 'Codex', 'parent', 'user'}
RUNG = {
    'Sonnet 5.5:medium': 1,
    'Sonnet 5.5:high': 2, 'Opus 5.5:low': 2, 'gpt-6.1-sol:medium': 2,
    'gpt-6-luna:high': 2, 'gpt-6.1-terra:medium': 2,
    'Opus 5.5:medium': 3, 'gpt-6.1-sol:high': 3,
    'Opus 5.5:high': 4, 'gpt-6-astra:high': 4,
    'Opus 5.5:xhigh': 5, 'Fable 5.2:medium': 6, 'Fable 5.2:high': 7,
}


class Invalid(ValueError):
    pass


@dataclass
class Plan:
    rows: dict
    form: str
    orchestrator: Optional[tuple] = None
    reviews: Optional[int] = None
    review_points: Optional[list] = None
    fix_rounds: Optional[int] = None


def cells(line):
    return [cell.strip() for cell in line.strip().strip('|').split('|')]


def parse(text):
    lines = text.splitlines()
    headers = [i for i, line in enumerate(lines) if line.lstrip().startswith('|') and cells(line) == COLUMNS]
    one_lines = [line.strip() for line in lines if line.strip().startswith('Triage:')]
    if len(headers) + len(one_lines) != 1:
        raise Invalid('expected exactly one triage table or one-line form with the canonical columns')
    rows = {}
    if headers:
        start = headers[0]
        if start + 1 >= len(lines) or not all(re.fullmatch(r':?-{3,}:?', c) for c in cells(lines[start + 1])) or len(cells(lines[start + 1])) != len(COLUMNS):
            raise Invalid('missing nine-column Markdown separator')
        for line in lines[start + 2:]:
            if not line.lstrip().startswith('|'):
                break
            values = cells(line)
            if len(values) != len(COLUMNS):
                raise Invalid('wrong number of table columns')
            row = dict(zip(COLUMNS, values))
            try:
                number = int(row['#'])
                deps = [] if row['Starts after'] == '—' else [int(x.strip()) for x in row['Starts after'].split(',')]
            except ValueError as exc:
                raise Invalid('step numbers and dependencies must be integers or —') from exc
            row['deps'] = deps
            add_row(rows, number, row)
        form = 'table'
    else:
        # Read allocations anywhere on the line; annotations are free text.
        entries = re.finditer(
            r'(?<!\w)(\d+)\s+([^·,;()]+?)\s*·\s*(\S+)\s+'
            r'\((subagent|Codex|parent|user)\)',
            one_lines[0][len('Triage:'):])
        for match in entries:
            number, model, level, runner = match.groups()
            row = dict(zip(COLUMNS, [number, 'Work', model.strip(), level, runner, '—', '—', '—', '—']))
            row['deps'] = []
            add_row(rows, int(number), row)
        if not rows:
            raise Invalid('malformed one-line entry: no row entries')
        if len(rows) > 5:
            raise Invalid('one-line form is limited to five rows')
        form = 'one-line'
    if not rows:
        raise Invalid('empty triage')
    for number, row in rows.items():
        model, level = row['Model'], row['Level']
        if row['Run as'] not in RUN_AS:
            raise Invalid(f'row {number}: unknown Run as')
        if row['Run as'] == 'user':
            if (model, level) != ('—', '—'):
                raise Invalid(f'row {number}: user requires — model and level')
        elif model not in MODELS or level not in LEVELS:
            raise Invalid(f'row {number}: unknown model or level')
        if len(row['deps']) != len(set(row['deps'])):
            raise Invalid(f'row {number}: repeated dependency')
        if any(dep not in rows for dep in row['deps']):
            raise Invalid(f'row {number}: dependency does not exist')
    plan = Plan(rows, form)
    waves(plan)  # Also detects cycles.
    check_ownership(plan)
    orchestrator = re.search(r'Orchestrator:\s*(.+?)\s*·\s*(low|medium|high|xhigh)\b', text)
    if orchestrator:
        plan.orchestrator = orchestrator.groups()
        if plan.orchestrator[0] not in MODELS:
            raise Invalid('unknown orchestrator model')
    elif 'Orchestrator:' in text:
        raise Invalid('malformed orchestrator')
    reviews = re.search(r'Reviews:\s*(\d+)(?:,\s*at\s+([\d, and]+))?', text)
    if reviews:
        plan.reviews = int(reviews[1])
        plan.review_points = [int(x) for x in re.findall(r'\d+', reviews[2] or '')]
    fixes = re.search(r'Fix rounds:\s*(\d+)', text)
    if fixes:
        plan.fix_rounds = int(fixes[1])
    return plan


def add_row(rows, number, row):
    if number < 1 or number in rows:
        raise Invalid('step numbers must be positive and unique')
    rows[number] = row


def waves(plan):
    result, active = {}, set()

    def visit(number):
        if number in active:
            raise Invalid('dependency cycle')
        if number not in result:
            active.add(number)
            result[number] = 1 + max((visit(dep) for dep in plan.rows[number]['deps']), default=0)
            active.remove(number)
        return result[number]

    for number in plan.rows:
        visit(number)
    return result


def dependencies(plan):
    """Return all ancestors after parse/waves has validated the DAG."""
    result = {}

    def visit(number):
        if number not in result:
            ancestors = set(plan.rows[number]['deps'])
            for dep in plan.rows[number]['deps']:
                ancestors.update(visit(dep))
            result[number] = ancestors
        return result[number]

    for number in plan.rows:
        visit(number)
    return result


def check_ownership(plan):
    schedule, owners = waves(plan), []
    for number, row in plan.rows.items():
        if row['Owns'] == '—':
            continue
        for item in row['Owns'].split(','):
            item = item.strip()
            # Unquoted possessive descriptions refer only to this row's work.
            if item.startswith('its '):
                continue
            item = item.strip('`').strip()
            if not item:
                raise Invalid(f'row {number}: empty Owns entry; use — for none')
            if item == '—':
                raise Invalid(f'row {number}: use — alone for no ownership')
            # Normalize common lexical path aliases without consulting the filesystem.
            path = normpath(item)
            for wave, owner, other in owners:
                if wave == schedule[number] and owner != number and (
                        path == other or path.startswith(other.rstrip('/') + '/')
                        or other.startswith(path.rstrip('/') + '/')
                        or path == '.' or other == '.'):
                    raise Invalid(f'same-wave ownership collision: rows {owner}, {number} overlap at {item}')
            owners.append((schedule[number], number, path))


def is_review(row):
    return 'review' in re.findall(r'\b\w+\b', row['Row'].lower())[:2]


def model_family(model):
    return 'Codex' if model.startswith('gpt-') else model.split()[0]


def score(expected, plan):
    failures, charges = [], []
    schedule = waves(plan)
    ancestors = dependencies(plan)
    specs = expected['steps']
    review_rows = [n for n, row in plan.rows.items() if is_review(row)]
    # This fixture measures whether a trivial task is over-planned. The session
    # stays as it is; its model declaration and allocation do not add failures.
    if expected['name'] == 'trivial':
        if len(plan.rows) > 2:
            failures.append('trivial task has a full table or one-line form of more than two rows')
        if review_rows:
            failures.append('trivial task must not have a review row')
        return failures, charges, 0
    if set(plan.rows) != {int(n) for n in specs}:
        failures.append('step numbers differ from the fixture; keep steps intact')
    if expected['orchestrator'] and plan.orchestrator != tuple(expected['orchestrator'].split(':')):
        failures.append('orchestrator differs from the accepted choice')
    if any(n not in expected['review_points'] for n in review_rows) or len(review_rows) > expected['reviews']:
        failures.append('review at an unaccepted point or too many reviews')
    if plan.form == 'table' and expected['name'] != 'trivial':
        if plan.reviews is None or plan.fix_rounds is None:
            failures.append('table must declare Reviews and Fix rounds')
        if plan.reviews != len(review_rows) or set(plan.review_points or []) != set(review_rows):
            failures.append('review declaration does not match review rows')
        if len(review_rows) < expected['reviews']:
            failures.append('missing accepted review')
    if plan.reviews is not None and plan.reviews > expected['reviews']:
        failures.append('too many declared reviews')
    if plan.fix_rounds is not None and plan.fix_rounds > expected['fix_rounds']:
        failures.append('too many fix rounds')
    for number, row in plan.rows.items():
        spec = specs.get(str(number))
        if spec is None:
            continue
        accepted = spec['accepted']
        pair = row['Model'] + ':' + row['Level']
        role_accepted = row['Run as'] in accepted
        pairs = [p for p in accepted if ':' in p]
        if row['Run as'] == 'user' and 'user' not in accepted:
            failures.append(f'row {number}: user is not an accepted runner')
        if 'user' in accepted and row['Run as'] != 'user':
            failures.append(f'row {number}: gate must run as user')
        if row['Run as'] == 'parent':
            if (row['Model'], row['Level']) != plan.orchestrator:
                failures.append(f'row {number}: parent model and level differ from orchestrator')
        if accepted == ['parent'] and not role_accepted:
            failures.append(f'row {number}: work must stay on parent')
        if pair == 'Opus 5.5:low' and row['Run as'] != 'parent':
            failures.append(f'row {number}: Opus low requires parent')
        forbidden = set(spec.get('never', []))
        if model_family(row['Model']) in forbidden or row['Run as'] in forbidden:
            failures.append(f'row {number}: forbidden model family or runner ({", ".join(sorted(forbidden))})')
        if row['Model'] == 'gpt-6-luna' and pair not in accepted:
            failures.append(f'row {number}: gpt-6-luna requires explicit fixture acceptance')
        if spec['floor']:
            minimum = RUNG[spec['floor_minimum']]
            # Parent-bound work retains the session model/level, but never loses
            # its floor. Family exclusions still apply to parent rows above.
            allowed_models = {p.split(':')[0] for p in pairs}
            family_ok = (role_accepted and row['Run as'] == 'parent') or row['Model'] in allowed_models
            if not family_ok or RUNG.get(pair, -1) < minimum or row['Run as'] == 'Codex':
                failures.append(f'row {number}: missed floor ({spec["floor_kind"]})')
        if (plan.form == 'table' and row['Owns'] == '—' and row['Run as'] != 'user'
                and not is_review(row) and not spec.get('read_only', False)):
            failures.append(f'row {number}: writing row has no ownership')
        missing = set(spec['required_dependencies']) - ancestors[number]
        if missing:
            failures.append(f'row {number}: missing required dependency {sorted(missing)}')
        predecessor = spec['chain_predecessor']
        if predecessor in schedule and schedule[number] <= schedule[predecessor]:
            failures.append(f'row {number}: split chain shares or precedes predecessor wave')
        if not role_accepted and row['Run as'] != 'user':
            ceiling = max((RUNG[p] for p in pairs), default=0)
            minimum = min((RUNG[p] for p in pairs), default=0)
            rung = RUNG.get(pair)
            if rung is None:
                failures.append(f'row {number}: model:level has no scoring rung')
            elif ceiling and rung > ceiling:
                charges.append((number, rung - ceiling, 'above accepted rung range'))
            elif pair not in accepted and minimum:
                if rung < minimum and (spec['floor'] or is_review(row)):
                    failures.append(f'row {number}: below accepted rung range')
                else:
                    charges.append((number, 2, 'outside accepted set'))
        permitted = set(spec['required_dependencies'] + spec['optional_dependencies'])
        baseline = max((schedule[d] for d in row['deps'] if d in permitted), default=0)
        forbidden_deps = set(spec['forbidden_dependencies'])
        for dep in row['deps']:
            if dep not in permitted and dep not in forbidden_deps and schedule[dep] > baseline:
                charges.append((number, 1, 'unneeded dependency delays row'))
        for dep in sorted(ancestors[number] & forbidden_deps):
            # A permitted intermediary must not hide a forbidden wait. Only
            # independent permitted prerequisites can make that wait redundant.
            independent_baseline = max(
                (schedule[d] for d in row['deps'] if d in permitted
                 and d != dep and dep not in ancestors[d]), default=0)
            if schedule[dep] > independent_baseline:
                charges.append((number, 1, 'unneeded dependency delays row (must not wait for this step)'))
        if spec['codex_first'] and row['Run as'] != 'Codex' and not bypass_reason(row):
            charges.append((number, 1, 'Codex first bypassed without a reason'))
    points = sum(points for _, points, _ in charges)
    return failures, charges, points


def bypass_reason(row):
    # Require an explanation of runner choice; a generic test name is not a reason.
    text = row['Check'] + ' ' + row['Escalate if']
    return bool(re.search(r'\b(?:reason|not Codex)\s*:\s*\S', text, re.I))


def evaluate(name, text):
    expected = json.loads((ROOT / 'fixtures' / name / 'expected.json').read_text())
    return score(expected, parse(text))


def report(name, text):
    try:
        failures, charges, points = evaluate(name, text)
    except Invalid as exc:
        failures, charges, points = [str(exc)], [], 0
    print('| Result | Row | Points | Reason |')
    print('|---|---|---|---|')
    for reason in failures:
        print(f'| FAIL | — | — | {reason} |')
    for number, cost, reason in charges:
        print(f'| Penalty | {number} | {cost} | {reason} |')
    passed = not failures and points <= 3
    print(f'| {"PASS" if passed else "FAIL"} | Total | {points} | Pass bar: at most 3 points and no failures |')
    return 0 if passed else 1


def selftest():
    count = 0

    def check(condition, label):
        nonlocal count
        if not condition:
            raise AssertionError(label)
        count += 1
        print('PASS ' + label)

    references = {}
    for name in ('swarm', 'chain', 'mixed', 'trivial', 'floor'):
        text = (ROOT / 'reference' / (name + '.md')).read_text()
        references[name] = text
        parse(text)
        fails, _, points = evaluate(name, text)
        check(not fails and points == 0, f'reference/{name}.md: lint accepted, 0 points')
    cases = [
        ('missed-floor', 'floor', 'missed floor'),
        ('split-chain', 'chain', 'split chain'),
        ('all-opus-high', 'swarm', 'above accepted rung range'),
        ('review-every-row', 'mixed', 'unaccepted point'),
        ('trivial-full-table', 'trivial', 'trivial task has a full table'),
        ('sonnet-reviewers', 'swarm', 'below accepted rung range'),
        ('secrets-sonnet-parent', 'floor', 'row 3: missed floor (secrets)'),
        ('video-prompts-codex', 'chain', 'forbidden model family or runner (Codex)'),
        ('overlapping-ownership', 'swarm', 'same-wave ownership collision'),
        ('mixed-ownership', 'swarm', 'same-wave ownership collision'),
        ('empty-owns', 'swarm', 'empty Owns entry'),
        ('final-review-sonnet', 'mixed', 'row 10: below accepted rung range'),
        ('outside-accepted-set', 'swarm', 'outside accepted set'),
        ('parent-mismatch', 'swarm', 'parent model and level differ from orchestrator'),
        ('missing-writing-owns', 'swarm', 'writing row has no ownership'),
        ('opus-low-subagent', 'mixed', 'Opus low requires parent'),
        ('generic-bypass', 'swarm', 'Codex first bypassed without a reason'),
    ]
    for filename, fixture, reason in cases:
        try:
            fails, charges, points = evaluate(fixture, (ROOT / 'wrong' / (filename + '.md')).read_text())
        except Invalid as exc:
            fails, charges, points = [str(exc)], [], 0
        reasons = '\n'.join(fails + [item[2] for item in charges])
        check((bool(fails) or points > 3) and reason in reasons,
              f'wrong/{filename}.md: rejected ({reason}; {points} points)')
    for label, text in [
        ('unknown model', references['swarm'].replace('gpt-6.1-sol', 'unknown-model', 1)),
        ('dependency cycle', references['swarm'].replace('| subagent | — |', '| subagent | 11 |', 1)),
        ('unknown dependency', references['swarm'].replace('| Codex | 1 |', '| Codex | 99 |', 1)),
        ('ownership collision', references['swarm'].replace('plugins/json.py', 'plugins/csv.py')),
        ('unknown level', references['swarm'].replace('| medium | Codex', '| extreme | Codex', 1)),
    ]:
        try:
            parse(text)
        except Invalid:
            check(True, 'lint rejects ' + label)
        else:
            check(False, 'lint rejects ' + label)
    for description in ('its test', 'its tests', 'its page', 'its acceptance notes'):
        text = references['swarm'].replace('`tests/test_csv.py`', description).replace(
            '`tests/test_json.py`', description)
        parse(text)
        check(True, 'lint accepts row-local ' + description)
    for label, first, second in [
        ('same path beside row-local descriptions', '`plugins/csv.py`, its test',
         '`plugins/csv.py`, its test'),
        ('directory before contained path', '`plugins/`, its tests',
         '`plugins/json.py`, its tests'),
        ('contained path before directory', '`plugins/csv.py`, its page',
         '`plugins/`, its page'),
        ('shared unquoted name', '`plugins/csv.py`, shared.py, its test',
         '`plugins/json.py`, shared.py, its test'),
        ('quoted possessive name', '`plugins/csv.py`, `its test`',
         '`plugins/json.py`, `its test`'),
    ]:
        text = references['swarm'].replace('`plugins/csv.py`, `tests/test_csv.py`', first).replace(
            '`plugins/json.py`, `tests/test_json.py`', second)
        try:
            parse(text)
        except Invalid as exc:
            check('same-wave ownership collision' in str(exc), 'lint rejects ' + label)
        else:
            check(False, 'lint rejects ' + label)
    floor = parse(references['floor'])
    floor.rows[6]['Run as'] = 'parent'
    floor.rows[6]['Model'], floor.rows[6]['Level'] = 'Opus 5.5', 'high'
    expected = json.loads((ROOT / 'fixtures/floor/expected.json').read_text())
    check(any('gate' in f for f in score(expected, floor)[0]), 'gate requires user')
    swarm_expected = json.loads((ROOT / 'fixtures/swarm/expected.json').read_text())
    plan = parse(references['swarm'])
    plan.rows[9]['deps'].append(2)
    check(score(swarm_expected, plan)[2] == 1, 'delaying forbidden dependency costs one point')
    plan.rows[9]['deps'].append(3)
    check(score(swarm_expected, plan)[2] == 2, 'tied delaying dependencies each cost one point')
    plan = parse(references['swarm'])
    plan.rows[8]['deps'].append(1)
    check(score(swarm_expected, plan)[2] == 0, 'redundant dependency without delay costs zero points')
    plan = parse(references['swarm'])
    plan.rows[2].update({'Run as': 'subagent', 'Check': '—', 'Escalate if': '—'})
    check(score(swarm_expected, plan)[2] == 1, 'unexplained Codex bypass costs one point')
    plan.rows[2]['Check'] = 'Run plugin tests'
    check(score(swarm_expected, plan)[2] == 1, 'a test name alone does not explain a Codex bypass')
    plan.rows[2]['Check'] = 'requires pytest because tests are needed'
    check(score(swarm_expected, plan)[2] == 1, 'generic requires/because text does not explain a Codex bypass')
    plan.rows[2]['Check'] = 'Reason: Codex unavailable for local tooling'
    check(score(swarm_expected, plan)[2] == 0, 'explained Codex bypass costs zero points')
    plan.rows[2]['Check'] = 'not Codex: local tooling unavailable'
    check(score(swarm_expected, plan)[2] == 0, 'not Codex marker explains a bypass')
    plan = parse(references['swarm'])
    plan.fix_rounds = 2
    check('too many fix rounds' in score(swarm_expected, plan)[0], 'fix round cap enforced')
    plan = parse(references['swarm'])
    plan.rows[2]['deps'] = []
    check(any('missing required dependency' in f for f in score(swarm_expected, plan)[0]), 'required dependency enforced')
    check(parse('Triage: 1 Opus 5.5·low (parent) · 2 gpt-6.1-sol·medium (Codex) · gate before push.').form == 'one-line', 'contract one-line example accepted')
    check(parse('Triage: 1 Opus 5.5·low (parent) · 2 Opus 5.5·low (parent) · floor: none · gate before push.').form == 'one-line', 'one-line floor annotation accepted')
    trivial = parse(references['trivial'])
    table = '| ' + ' | '.join(COLUMNS) + ' |\n|' + '---|' * len(COLUMNS) + '\n'
    for row in trivial.rows.values():
        table += '| ' + ' | '.join(row[c] for c in COLUMNS) + ' |\n'
    fails, _, points = evaluate('trivial', table)
    check(not fails and points == 0, 'trivial two-row table accepted at zero points')
    fails, _, points = evaluate('trivial', 'Orchestrator: Opus 5.5 · low (session unchanged).\n' + references['trivial'])
    check(not fails and points == 0, 'trivial ignores orchestrator declaration')
    fails, _, points = evaluate('trivial', 'Triage: 1 Sonnet 5.5·medium (subagent) · 2 Opus 5.5·xhigh (subagent).')
    check(not fails and points == 0, 'trivial measures row and review counts only')
    fails, _, _ = evaluate('trivial', table.replace('| Work |', '| Final review |', 1))
    check(any('review row' in f for f in fails), 'trivial review row rejected')
    fails, _, _ = evaluate('trivial', 'Triage: 1 Opus 5.5·low (parent) · 2 Opus 5.5·low (parent) · 3 Opus 5.5·low (parent).')
    check(any('more than two rows' in f for f in fails), 'trivial three-row one-line form rejected')
    for title in ('Review the change', 'Final review of the change', 'Join review of the change', 'Security review of the change'):
        plan = parse(references['swarm'])
        plan.rows[11]['Row'] = title
        check(not score(swarm_expected, plan)[0], 'review recognition: ' + title)
    check(not is_review({'Row': 'Prepare for review'}), 'review beyond first two words is ordinary work')
    plan = parse(references['swarm'])
    plan.rows[9].update({'Model': 'Sonnet 5.5', 'Level': 'medium'})
    fails, charges, points = score(swarm_expected, plan)
    check(not fails and points == 2 and charges[0][2] == 'outside accepted set', 'ordinary under-allocation costs two points')
    plan = parse(references['swarm'])
    plan.rows[2]['Model'] = 'gpt-6.1-terra'
    check(score(swarm_expected, plan)[2] == 2, 'unlisted pair at an accepted rung costs two points')
    plan.rows[2].update({'Model': 'gpt-6-luna', 'Level': 'high'})
    check(any('explicit fixture acceptance' in f for f in score(swarm_expected, plan)[0]), 'luna requires explicit acceptance despite rung 2')
    luna_expected = json.loads(json.dumps(swarm_expected))
    luna_expected['steps']['2']['accepted'].append('gpt-6-luna:high')
    fails, _, points = score(luna_expected, plan)
    check(RUNG['gpt-6-luna:high'] == 2 and not fails and points == 0, 'explicitly accepted luna remains rung 2 at zero points')
    plan = parse(references['swarm'])
    plan.rows[2]['Run as'] = 'parent'
    check(any('differ from orchestrator' in f for f in score(swarm_expected, plan)[0]), 'unlisted parent must still match orchestrator')
    plan = parse(references['swarm'])
    plan.rows[1].update({'Model': 'Opus 5.5', 'Level': 'high', 'Run as': 'parent'})
    fails, _, points = score(swarm_expected, plan)
    check(not fails and points == 0, 'interface contract on the Opus high parent accepted')
    plan.rows[1]['Level'] = 'medium'
    check(any('differ from orchestrator' in f for f in score(swarm_expected, plan)[0]), 'parent level must match orchestrator')
    for fixture, number in (('mixed', 9), ('floor', 7)):
        plan = parse(references[fixture])
        plan.rows[number]['Run as'] = 'subagent'
        expected = json.loads((ROOT / 'fixtures' / fixture / 'expected.json').read_text())
        check(any('work must stay on parent' in f for f in score(expected, plan)[0]), fixture + ' production verification requires parent')
    plan = parse(references['floor'])
    plan.orchestrator = ('Opus 5.5', 'high')
    plan.rows[3]['Run as'] = 'parent'
    plan.rows[7]['Level'] = 'high'
    floor_expected = json.loads((ROOT / 'fixtures/floor/expected.json').read_text())
    fails, _, points = score(floor_expected, plan)
    check(not fails and points == 0, 'secrets floor and production verification on matching Opus high parent')
    for fixture, number in (('mixed', 5), ('mixed', 6), ('floor', 3), ('floor', 4)):
        expected = json.loads((ROOT / 'fixtures' / fixture / 'expected.json').read_text())
        for model, level in (('gpt-6-astra', 'high'), ('Sonnet 5.5', 'high'), ('Fable 5.2', 'high')):
            plan = parse(references[fixture])
            plan.rows[number].update({'Model': model, 'Level': level})
            check(any('forbidden model family' in f for f in score(expected, plan)[0]), f'{fixture} row {number} forbids {model}')
    plan = parse(references['swarm'])
    plan.rows[3]['Owns'] = '`plugins/csv.py`'
    plan.rows[3]['deps'] = [1, 2]
    check_ownership(plan)
    check(True, 'ordered rows may own the same file')
    # At the bar, pass; one point above the bar, reject, without another failure.
    plan = parse(references['swarm'])
    plan.rows[8].update({'Model': 'Opus 5.5', 'Level': 'high'})
    fails, _, points = score(swarm_expected, plan)
    check(not fails and points == 3, 'three-point pass boundary')
    plan.rows[9]['Level'] = 'high'
    fails, _, points = score(swarm_expected, plan)
    check(not fails and points == 4, 'four-point rejection boundary')
    # Regression cases from the five live skill runs (2.0.0 outputs).
    for name, expected_points in (('chain', 0), ('mixed', 1), ('trivial', 0), ('floor', 1)):
        fails, _, points = evaluate(name, (ROOT / 'live' / (name + '.md')).read_text())
        check(not fails and points == expected_points and points <= 3,
              f'live/{name}.md: accepted, {points} points (expected {expected_points})')
    # The 2.0.0 swarm run used a Fable orchestrator; since 2.3.0 that is the only failure.
    fails, _, points = evaluate('swarm', (ROOT / 'live' / 'swarm.md').read_text())
    check(fails == ['orchestrator differs from the accepted choice'] and points == 2,
          'live/swarm.md: rejected only for its 2.0 Fable orchestrator')
    plan = parse(references['mixed'])
    plan.rows[8]['deps'] = [10]
    expected = json.loads((ROOT / 'fixtures/mixed/expected.json').read_text())
    check(not score(expected, plan)[0], 'required dependency accepted through an intermediate row')
    plan.rows[10]['deps'].remove(7)
    check(any('row 8: missing required dependency [7]' == f for f in score(expected, plan)[0]),
          'required dependency still fails when absent from all paths')
    plan = parse(references['swarm'])
    plan.rows[9]['deps'] = [10]
    fails, charges, points = score(swarm_expected, plan)
    forbidden_charges = [c for c in charges if 'must not wait' in c[2]]
    check(not fails and len(forbidden_charges) == 6 and points == 7,
          'forbidden dependencies detected through a review intermediary')
    allowed_intermediary = json.loads(json.dumps(swarm_expected))
    allowed_intermediary['steps']['9']['optional_dependencies'] = [10]
    check(score(allowed_intermediary, plan)[2] == 6,
          'optional intermediary cannot hide forbidden dependencies')
    plan.rows[9]['deps'].extend([2, 3])
    check(score(allowed_intermediary, plan)[2] == 6,
          'direct and indirect forbidden paths charge each ancestor only once')
    plan = parse(references['swarm'])
    plan.orchestrator = ('Sonnet 5.5', 'high')
    plan.rows[2].update({'Model': 'Sonnet 5.5', 'Level': 'high', 'Run as': 'parent',
                         'Check': 'Reason: local tooling'})
    parent_expected = json.loads(json.dumps(swarm_expected))
    parent_expected['orchestrator'] = None
    fails, _, points = score(parent_expected, plan)
    check(not fails and points == 0, 'matching parent at an accepted pair needs no parent listing')
    plan.orchestrator = ('Opus 5.5', 'high')
    plan.rows[2].update({'Model': 'Opus 5.5', 'Level': 'high'})
    fails, _, points = score(parent_expected, plan)
    check(not fails and points == 2, 'unlisted parent above accepted range pays usual rung points')
    plan = parse(references['mixed'])
    plan.rows[7].update({'Model': 'Opus 5.5', 'Level': 'medium', 'Run as': 'parent'})
    check(any('row 7: missed floor' in f for f in score(expected, plan)[0]),
          'matching unlisted parent below a floor still fails')
    plan = parse(references['chain'])
    plan.rows[2]['Run as'] = 'subagent'
    chain_expected = json.loads((ROOT / 'fixtures/chain/expected.json').read_text())
    check(any('work must stay on parent' in f for f in score(chain_expected, plan)[0]),
          'chain parent-bound row cannot be delegated')
    plan = parse(references['swarm'].replace('Reviews: 2, at 10 and 11.',
                                           'Reviews: 2, at 10 and 11 per review gate.').replace(
                                               'Fix rounds: 1.', 'Fix rounds: 1 per link gate.'))
    check(not score(swarm_expected, plan)[0], 'header counts accept trailing wording')
    plan = parse(references['swarm'].replace('Reviews: 2, at 10 and 11.',
                                           'Reviews: 3, at 10 and 11 per review gate.').replace(
                                               'Fix rounds: 1.', 'Fix rounds: 2 per link gate.'))
    fails, _, _ = score(swarm_expected, plan)
    check('too many declared reviews' in fails and 'too many fix rounds' in fails,
          'trailing header wording does not bypass budget caps')
    plan = parse('Triage: checks first · 1 Opus 5.5·medium (parent), starts after 0 · '
                 'reason: tiny · 2 Opus 5.5·medium (parent), existing tests pass · approval: none.')
    check(set(plan.rows) == {1, 2}, 'one-line allocations accept annotations before and after entries')
    try:
        parse('Triage: check: tests pass · reason: tiny · approval: none.')
    except Invalid as exc:
        check('no row entries' in str(exc), 'one-line form with no allocations is malformed')
    else:
        check(False, 'one-line form with no allocations is malformed')
    print(f'SELFTEST PASS: {count} checks')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--selftest', action='store_true')
    modes.add_argument('--lint', type=Path, metavar='FILE')
    parser.add_argument('name', nargs='?', choices=['swarm', 'chain', 'mixed', 'trivial', 'floor'])
    parser.add_argument('triage', nargs='?', type=Path)
    args = parser.parse_args()
    if (args.selftest or args.lint) and (args.name or args.triage):
        parser.error('modes cannot be combined with fixture arguments')
    try:
        if args.selftest:
            return selftest()
        if args.lint:
            plan = parse(args.lint.read_text())
            print(f'LINT PASS: {len(plan.rows)} rows ({plan.form})')
            return 0
        if not args.name or not args.triage:
            parser.error('provide <name> <triage.md>, --lint <file.md>, or --selftest')
        return report(args.name, args.triage.read_text())
    except (Invalid, OSError, ValueError, AssertionError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
