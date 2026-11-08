#!/usr/bin/env python3
"""Persistent, private daily Atlas packs using the existing assurance reporter.

No network, credentials, model calls, ledger writes, publishing, or schedulers.
Immutable generations become visible only after digest verification. Repeated
source snapshots are counted once; reports do not become new measurements.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime, timezone, date
sys.path.insert(0, str(Path(__file__).resolve().parent))
import assurance_report as report
from assurance_core import canonical, digest, locked_file

VERSION = 'csoai.atlas-daily/1.0'
RENDER_REVISION = 'comparison-baseline/1'
RENDER_KEYS = ('render_revision', 'parent_generation', 'comparison_from_generation',
               'comparison_from_report_id', 'comparison_selection',
               'supersedes_generation', 'superseded_artifacts', 'correction_reason', 'legacy_index_sha256')
CORRECTED_ARTIFACTS = ('manifest.json', 'changes.json', 'report.md', 'index.html')
MAX_GENERATIONS = 512
MAX_INDEX_BYTES = 2 * 1024 * 1024


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def checked_path(root, name):
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('unsafe artifact path')
    return path


def read_json(path, limit=MAX_INDEX_BYTES):
    if path.is_symlink():
        raise ValueError('symlink refused')
    with path.open('rb') as f:
        raw = f.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('read bound exceeded')
    value = json.loads(raw)
    canonical(value)
    return value


def capture(lane, target):
    """Read each exact allowlisted source, then confirm it has not changed."""
    records = []
    for name in report.INPUTS:
        path = checked_path(lane, name)
        if not path.is_file():
            raise ValueError('required source unavailable: ' + name)
        with path.open('rb') as f:
            raw = f.read(report.MAX_BYTES + 1)
        if len(raw) > report.MAX_BYTES:
            raise ValueError('source exceeds bound: ' + name)
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError('source is not an object: ' + name)
        canonical(obj)
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        records.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
    for row in records:
        path = checked_path(lane, row['path'])
        with path.open('rb') as f:
            raw = f.read(report.MAX_BYTES + 1)
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('source changed during capture: ' + row['path'])
    return records


def read_archive(root):
    entries = []
    folder = checked_path(root, 'generations')
    if not folder.exists():
        return entries
    paths = sorted(folder.iterdir())
    if len(paths) > MAX_GENERATIONS:
        raise ValueError('retention limit reached; owner archival decision required')
    for path in paths:
        if path.is_symlink() or not path.is_dir() or not path.name.startswith('g-'):
            raise ValueError('invalid generation path')
        receipt = read_json(path / 'atlas-receipt.json')
        read_json(path / 'manifest.json')  # Bound the manifest before verification.
        accepted = report.verify(path)
        if receipt.get('schema') != VERSION or receipt.get('generation') != path.name:
            raise ValueError('invalid generation receipt')
        if accepted['report_id'] != receipt['report_id']:
            raise ValueError('generation/report identity mismatch')
        current = read_json(path / 'latest.json')
        source_id = digest([{'path': s['path'], 'sha256': s['sha256']} for s in current['sources']])
        if current['day'] != receipt['day'] or current['source_as_of'] != receipt['source_as_of']:
            raise ValueError('generation date mismatch')
        if source_id != receipt['source_snapshot_id']:
            raise ValueError('source snapshot identity mismatch')
        expected_name = generation_name(receipt)
        if path.name != expected_name:
            raise ValueError('generation name mismatch')
        entries.append({**receipt, 'statistics': current['statistics'],
                        'finding_ids': sorted(f['id'] for f in current['findings']),
                        'path': 'generations/' + path.name + '/index.html'})
    entries.sort(key=lambda e: (e['day'], e['first_generated_at'], e['generation']))
    by_generation = {e['generation']: e for e in entries}
    for entry in entries:
        if 'render_revision' in entry:
            verify_render(root, entry, by_generation)
    # Reject cycles even if every local digest/manifest has been regenerated.
    for entry in entries:
        seen = set()
        while entry is not None and 'render_revision' in entry:
            name = entry['generation']
            if name in seen:
                raise ValueError('render parent cycle')
            seen.add(name)
            entry = by_generation.get(entry['parent_generation'])
    return entries


def legacy_evidence_index(entries, current_generation):
    sources = {e['source_snapshot_id'] for e in entries}
    previous = next((e for e in reversed(entries) if e['generation'] != current_generation), None)
    current = next(e for e in entries if e['generation'] == current_generation)
    prev_ids = set(previous['finding_ids']) if previous else set()
    now_ids = set(current['finding_ids'])
    older_sources = {e['source_snapshot_id'] for e in entries if e['generation'] != current_generation}
    return {'schema': 'csoai.atlas-evidence-index/1.0', 'mode': 'PRIVATE_REVIEW',
            'current_generation': current_generation, 'reports': entries,
            'unique_source_snapshots': len(sources), 'report_generations': len(entries),
            'new_source_snapshot': current['source_snapshot_id'] not in older_sources,
            'comparison': {'baseline_available': previous is not None,
                           'from_report_id': previous['report_id'] if previous else None,
                           'to_report_id': current['report_id'],
                           'new_finding_ids': sorted(now_ids-prev_ids),
                           'carried_finding_ids': sorted(now_ids & prev_ids),
                           'no_longer_observed_ids': sorted(prev_ids-now_ids),
                           'no_longer_observed_means_resolved': False},
            'new_model_measurements': 0, 'financial_valuation': None,
            'ip_ownership_verified': False, 'public_release_verified': False}


def generation_name(receipt):
    basis = {'version': VERSION, 'report_id': receipt['report_id']}
    if 'render_revision' in receipt:
        if receipt['render_revision'] != RENDER_REVISION:
            raise ValueError('unsupported render revision')
        basis.update({key: receipt[key] for key in RENDER_KEYS})
    return 'g-' + digest(basis)


def generation_dir(root, entry):
    return checked_path(root, 'generations/' + entry['generation'])


def superseded_hashes(root, parent):
    folder = generation_dir(root, parent)
    return {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
            for name in CORRECTED_ARTIFACTS}


def render_basis(root, report_id, parent, entries, legacy_index_raw=None):
    """The discovery pointer, never a timestamp sort, establishes the parent."""
    previous = parent
    supersedes = parent if parent and parent['report_id'] == report_id else None
    selection = 'PARENT_REPORT' if parent else 'FIRST_REPORT'
    if supersedes:
        if 'render_revision' in parent:
            raise ValueError('current corrected report must be reused')
        if legacy_index_raw is None:
            raise ValueError('legacy comparison index missing')
        legacy_entries = [e for e in entries if 'render_revision' not in e]
        expected = legacy_evidence_index(legacy_entries, parent['generation'])
        if canonical(json.loads(legacy_index_raw)) != canonical(expected):
            raise ValueError('legacy comparison index differs from retained history')
        previous = next((e for e in reversed(legacy_entries)
                         if e['generation'] != parent['generation']), None)
        selection = 'LEGACY_ARCHIVE_INDEX'
    if previous and (previous['report_id'] == report_id or
                     parent and previous['day'] > parent['day']):
        raise ValueError('comparison baseline is not a prior distinct report')
    return {'render_revision': RENDER_REVISION,
            'parent_generation': parent['generation'] if parent else None,
            'comparison_from_generation': previous['generation'] if previous else None,
            'comparison_from_report_id': previous['report_id'] if previous else None,
            'comparison_selection': selection,
            'supersedes_generation': supersedes['generation'] if supersedes else None,
            'superseded_artifacts': superseded_hashes(root, supersedes) if supersedes else {},
            'correction_reason': 'COMPARISON_BASELINE_RENDERING' if supersedes else None,
            'legacy_index_sha256': hashlib.sha256(legacy_index_raw).hexdigest() if supersedes else None}


def verify_render(root, entry, by_generation):
    if entry['signature_state'] != 'UNSIGNED' or entry['public_release_verified'] is not False:
        raise ValueError('unexpected rendering authority claim')
    parent_name = entry['parent_generation']
    if parent_name is not None and parent_name not in by_generation:
        raise ValueError('render parent unavailable')
    parent = by_generation.get(parent_name)
    if parent and parent['day'] > entry['day']:
        raise ValueError('render parent postdates report')
    folder = generation_dir(root, entry)
    legacy_raw = None
    if entry['comparison_selection'] == 'LEGACY_ARCHIVE_INDEX':
        read_json(folder / 'legacy-evidence-index.json')
        legacy_raw = (folder / 'legacy-evidence-index.json').read_bytes()
    expected_basis = render_basis(root, entry['report_id'], parent,
                                  list(by_generation.values()), legacy_raw)
    if any(entry[key] != expected_basis[key] for key in RENDER_KEYS):
        raise ValueError('render comparison lineage mismatch')
    previous_entry = by_generation.get(entry['comparison_from_generation'])
    previous = read_json(generation_dir(root, previous_entry) / 'latest.json') if previous_entry else None
    current = read_json(folder / 'latest.json')
    expected_id = digest({'version': report.VERSION, 'day': current['day'], 'sources': current['sources']})
    if current['report_id'] != expected_id or current['statistics']['new_model_measurements'] != 0:
        raise ValueError('render report identity or measurement claim mismatch')
    timeline = report.history(folder)
    if len(timeline) != 1 or (folder / timeline[0]['path']).read_bytes() != (folder / 'latest.json').read_bytes():
        raise ValueError('render must retain its exact immutable report')
    delta = report.comparison_delta(current, previous)
    card = read_json(folder / 'card.json')
    expected_artifacts = {
        'changes.json': canonical(delta) + b'\n',
        'report.md': report.report_markdown(current, delta),
        'index.html': report.render_html(current, timeline, delta, card),
        'index.json': canonical({'schema': 'csoai.assurance-index/1.0', 'reports': timeline}) + b'\n',
        'findings.json': canonical({'report_id': current['report_id'], 'findings': current['findings']}) + b'\n'}
    for name, expected in expected_artifacts.items():
        if (folder / name).read_bytes() != expected:
            raise ValueError('render semantic mismatch: ' + name)
    required = set(expected_artifacts) | {'latest.json', 'card.json', 'mappings.csv',
                                        'atlas-receipt.json', timeline[0]['path']}
    if legacy_raw is not None:
        required.add('legacy-evidence-index.json')
    artifacts = read_json(folder / 'manifest.json')['artifacts']
    if len(artifacts) != len(required) or {row['path'] for row in artifacts} != required:
        raise ValueError('render manifest must cover every required artifact exactly once')


def evidence_index(entries, current_generation):
    current = next(e for e in entries if e['generation'] == current_generation)
    if 'render_revision' not in current:
        return legacy_evidence_index(entries, current_generation)
    baseline = current['comparison_from_generation']
    previous = next((e for e in entries if e['generation'] == baseline), None)
    index = legacy_evidence_index(entries, current_generation)
    prev_ids = set(previous['finding_ids']) if previous else set()
    now_ids = set(current['finding_ids'])
    index.update({'schema': 'csoai.atlas-evidence-index/1.1',
                  'unique_report_ids': len({e['report_id'] for e in entries}),
                  'render_generations': len(entries)})
    index['comparison'].update({
        'baseline_available': previous is not None,
        'from_generation': baseline,
        'from_report_id': previous['report_id'] if previous else None,
        'new_finding_ids': sorted(now_ids - prev_ids),
        'carried_finding_ids': sorted(now_ids & prev_ids),
        'no_longer_observed_ids': sorted(prev_ids - now_ids)})
    return index


def verify_discovery(out, entries):
    pointer = read_json(out / 'current.json')
    actual_index = read_json(out / 'evidence-index.json')
    expected = evidence_index(entries, pointer['generation'])
    if canonical(actual_index) != canonical(expected):
        raise ValueError('evidence index differs from verified generations')
    raw = (out / 'evidence-index.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != pointer['index_sha256']:
        raise ValueError('current index digest mismatch')
    current = next(e for e in entries if e['generation'] == pointer['generation'])
    if pointer.get('schema') != VERSION or pointer['report_id'] != current['report_id'] or pointer['path'] != current['path']:
        raise ValueError('current pointer mismatch')
    if (out / 'index.html').read_bytes() != landing(expected):
        raise ValueError('archive landing differs from verified index')
    return current, expected


def landing(index):
    rows = ''.join('<li><a href="%s">%s — %s</a></li>' %
                   (html.escape(e['path'], quote=True), html.escape(e['day']), e['report_id'][:16])
                   for e in reversed(index['reports']))
    current = next(e for e in index['reports'] if e['generation'] == index['current_generation'])
    counts = ('%s report IDs · %s render generations · %s unique source snapshots' %
              (index['unique_report_ids'], index['render_generations'], index['unique_source_snapshots'])
              if 'unique_report_ids' in index else '%s reports · %s unique source snapshots' %
              (index['report_generations'], index['unique_source_snapshots']))
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Council of AI — Evidence archive</title><style>body{font:17px system-ui;max-width:960px;margin:4rem auto;padding:1rem;background:#f5f7f6;color:#102a2a}a{color:#075e51}li{padding:.6rem}code{overflow-wrap:anywhere}.card{padding:2rem;background:white;border:1px solid #c8d5d1;border-radius:16px}</style>'
            '<main><p>COUNCIL OF AI · PRIVATE REVIEW ARCHIVE</p><h1>Daily evidence. Retained history.</h1><div class="card">'
            '<p><strong>%s</strong></p>'
            '<p>A repeated snapshot is not a new measurement. Hashes are not signatures, legal approval or financial value.</p>'
            '<p><a href="%s">Open the current evidence workspace →</a></p>'
            '<p><a href="evidence-index.json">Machine-readable evidence index</a></p></div><h2>Reports</h2><ul>%s</ul>'
            '<p>No publication, signing, payment, inference, training or execution is performed by this archive.</p></main></html>' %
            (counts, current['path'], rows)).encode()


def build_daily(lane, out, day):
    date.fromisoformat(day)
    lane, out = Path(lane), Path(out)
    if out.is_symlink() or out.resolve() == lane.resolve() or lane.resolve().is_relative_to(out.resolve()):
        raise ValueError('invalid output location')
    out.mkdir(parents=True, exist_ok=True)
    with locked_file(out / '.atlas.lock'):
        before = read_archive(out)
        parent = verify_discovery(out, before)[0] if before else None
        if not before and any((out / name).exists() for name in ('current.json', 'evidence-index.json')):
            raise ValueError('discovery exists without retained generations')
        if before and day < max(e['day'] for e in before):
            raise ValueError('daily current pointer cannot move backwards in date')
        staging_parent = checked_path(out, '.staging')
        staging_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='pack-', dir=staging_parent) as temp:
            scratch = Path(temp)
            inputs = scratch / 'inputs'; inputs.mkdir()
            records = capture(lane, inputs)
            draft = report.summarize(inputs, day)
            if parent and parent.get('render_revision') == RENDER_REVISION and parent['report_id'] == draft['report_id']:
                generation, reused = parent['generation'], True
            else:
                legacy_raw = ((out / 'evidence-index.json').read_bytes()
                              if parent and parent['report_id'] == draft['report_id'] else None)
                basis = render_basis(out, draft['report_id'], parent, before, legacy_raw)
                generation = generation_name({'report_id': draft['report_id'], **basis})
                dest = checked_path(out, 'generations') / generation
                if dest.exists():
                    raise ValueError('unpublished rendering already exists; owner recovery required')
                if len(before) >= MAX_GENERATIONS:
                    raise ValueError('retention limit reached; owner archive required')
                candidate = scratch / 'report'
                baseline_entry = next((e for e in before if e['generation'] == basis['comparison_from_generation']), None)
                baseline = read_json(generation_dir(out, baseline_entry) / 'latest.json') if baseline_entry else None
                result = report.build(inputs, candidate, day, baseline=baseline)
                receipt = {'schema': VERSION, 'generation': generation, **basis,
                           'report_id': result['report_id'], 'day': day,
                           'first_generated_at': utc(),
                           'source_snapshot_id': digest([{'path': s['path'], 'sha256': s['sha256']} for s in draft['sources']]),
                           'source_as_of': draft['source_as_of'],
                           'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           'signature_state': 'UNSIGNED', 'public_release_verified': False}
                extra = {'atlas-receipt.json': canonical(receipt) + b'\n'}
                if legacy_raw is not None:
                    extra['legacy-evidence-index.json'] = legacy_raw
                manifest = read_json(candidate / 'manifest.json')
                for name, raw in extra.items():
                    (candidate / name).write_bytes(raw)
                    manifest['artifacts'].append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
                report.atomic_write(candidate / 'manifest.json', canonical(manifest) + b'\n')
                report.verify(candidate)
                dest.parent.mkdir(exist_ok=True)
                os.rename(candidate, dest)
                reused = False
        entries = read_archive(out)
        index = evidence_index(entries, generation)
        report.atomic_write(out / 'evidence-index.json', canonical(index) + b'\n')
        report.atomic_write(out / 'index.html', landing(index))
        pointer = {'schema': VERSION, 'generation': generation, 'report_id': draft['report_id'],
                   'path': 'generations/' + generation + '/index.html',
                   'index_sha256': hashlib.sha256((out / 'evidence-index.json').read_bytes()).hexdigest()}
        report.atomic_write(out / 'current.json', canonical(pointer) + b'\n')
        return {'status': 'VERIFIED_PRIVATE_PACK', 'generation': generation,
                'report_id': draft['report_id'], 'reused': reused,
                'report_generations': index['report_generations'],
                'unique_report_ids': index['unique_report_ids'],
                'render_generations': index['render_generations'],
                'unique_source_snapshots': index['unique_source_snapshots'],
                'source_as_of': draft['source_as_of'], 'public_release_verified': False,
                'signature_state': 'UNSIGNED', 'new_model_measurements': 0}


def verify_archive(out):
    out = Path(out)
    with locked_file(out / '.atlas.lock'):
        entries = read_archive(out)
        current, expected = verify_discovery(out, entries)
    return {'status': 'ARCHIVE_VERIFIED', 'report_generations': len(entries),
            'unique_source_snapshots': expected['unique_source_snapshots'],
            'public_release_verified': False, 'signature_state': 'UNSIGNED'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build'); b.add_argument('--lane', type=Path, required=True)
    b.add_argument('--out',type=Path,required=True)
    b.add_argument('--date',default=datetime.now(timezone.utc).date().isoformat())
    v=sub.add_parser('verify'); v.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    try:
        result=build_daily(a.lane,a.out,a.date) if a.command=='build' else verify_archive(a.out)
        print(json.dumps(result,sort_keys=True)); return 0
    except (ValueError,OSError,KeyError,TypeError,StopIteration) as e:
        print(json.dumps({'status':'BLOCKED','error':str(e)}),file=sys.stderr); return 1


if __name__=='__main__':
    raise SystemExit(main())
