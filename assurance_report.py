#!/usr/bin/env python3
"""Build immutable daily readback reports from an allowlist of existing lane data.

No network, inference, private session ingestion, publishing, keys or valuation.
Source assertions are not independent measurements. Hashes are not signatures.
Run: python3 assurance_report.py build --lane PATH --out PATH [--date YYYY-MM-DD]
     python3 assurance_report.py verify --out PATH
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from datetime import date, datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent))
from assurance_core import canonical, digest, locked_file

VERSION = 'csoai.assurance-readback/1.0'
MAX_BYTES = 2 * 1024 * 1024
INPUTS = ('latest.json', 'frameworks/crosswalk.json', 'frameworks/obligation-index.json')
NAME = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,159}$')


def read_input(lane, name):
    root = lane.resolve()
    path = lane / name
    if not path.resolve().is_relative_to(root) or path.is_symlink():
        raise ValueError('source path escapes lane or is a symlink')
    if not path.exists():
        return None, {'path': name, 'state': 'MISSING', 'sha256': None}
    with path.open('rb') as f:
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('source exceeds bounded size: ' + name)
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError('source must be an object: ' + name)
    canonical(obj)
    meta = {'path': name, 'state': 'READ', 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    if isinstance(obj.get('_capture'), dict):
        cap = obj['_capture']
        meta['capture_kind'] = cap.get('kind', 'UNVERIFIED')
        meta['origin_sha256_reported'] = cap.get('origin_sha256')
        meta['origin_bytes_retained'] = cap.get('origin_bytes_retained') is True
    return obj, meta


def valid_count(value):
    return value if type(value) is int and value >= 0 else None


def date_text(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return None
        return parsed.isoformat().replace('+00:00', 'Z')
    except ValueError:
        return None


def safe_name(value):
    return value if isinstance(value, str) and NAME.fullmatch(value) else None


def finding(code, severity, title, evidence, action):
    return {'id': digest({'code': code, 'evidence': evidence})[:24], 'code': code,
            'severity': severity, 'state': 'OPEN', 'title': title,
            'source': evidence, 'review_state': 'PENDING_REVIEW',
            'evidence_status': 'OBSERVED_INPUT', 'next_action': action}


def summarize(lane, day):
    data, provenance = {}, []
    for name in INPUTS:
        data[name], meta = read_input(lane, name)
        provenance.append(meta)
    raw_latest = data['latest.json'] or {}
    latest = raw_latest.get('latest', {})
    if not isinstance(latest, dict):
        raise ValueError('latest must be an object')
    board = latest.get('board') or {}
    if not isinstance(board, dict):
        raise ValueError('board must be an object')
    matrix = data['frameworks/crosswalk.json'] or {}
    catalogue = data['frameworks/obligation-index.json'] or {}
    pairs = matrix.get('pairs', [])
    products = catalogue.get('obligations', [])
    if not isinstance(pairs, list) or not isinstance(products, list):
        raise ValueError('crosswalk pairs and product obligations must be arrays')
    findings, rows = [], []
    for meta in provenance:
        if meta['state'] == 'MISSING':
            findings.append(finding('SOURCE_MISSING', 'HIGH', 'Required readback source unavailable', meta['path'], 'Restore this source through its existing owner; do not substitute zero.'))
    unique_pairs = set()
    if isinstance(matrix.get('tiers'), dict) and any(v == 'x402-or-unreachable' for v in matrix['tiers'].values()):
        findings.append(finding('ACCESS_STATE_AMBIGUOUS', 'HIGH', 'Payment challenge and unreachable source are conflated', 'frameworks/crosswalk.json', 'Record HTTP 402, HTTP 403, timeout and validated response separately; do not infer paid access from failure.'))
    for p in pairs:
        if not isinstance(p, dict):
            raise ValueError('mapping row must be an object')
        axis, product, level = safe_name(p.get('axis')), safe_name(p.get('obligation')), p.get('relevance')
        if not axis or not product or level not in ('D', 'S', 'C'):
            findings.append(finding('INVALID_MAPPING', 'HIGH', 'Malformed mapping omitted', 'frameworks/crosswalk.json', 'Correct the mapping source and preserve a correction entry.'))
            continue
        key = (axis, product)
        if key in unique_pairs:
            findings.append(finding('DUPLICATE_MAPPING', 'MEDIUM', 'Duplicate axis/product mapping', 'frameworks/crosswalk.json', 'Deduplicate by axis and product; do not count copies as coverage.'))
            continue
        unique_pairs.add(key)
        rows.append({'id': digest({'axis': axis, 'product': product})[:24], 'axis': axis,
                     'product': product, 'relevance': {'D': 'DIRECT_HEURISTIC', 'S': 'SUPPORTING_HEURISTIC', 'C': 'CONTEXTUAL_HEURISTIC'}[level],
                     'evidence_status': 'MAPPING_ONLY', 'review_state': 'PENDING_REVIEW',
                     'source': 'frameworks/crosswalk.json', 'as_of': date_text(matrix.get('as_of')),
                     'legal_coverage': None, 'applicability': 'NOT_ASSESSED',
                     'measurement_id': None, 'provision_id': None,
                     'signature_verified': False, 'human_review_verified': False})
    product_ids = sorted({safe_name(o.get('id')) for o in products if isinstance(o, dict) and safe_name(o.get('id'))})
    findings.append(finding('PROVISION_COVERAGE_NOT_ESTABLISHED', 'HIGH', 'Product-level mappings are not article-level assessments', 'frameworks/obligation-index.json', 'Bind versioned provisions, applicability criteria and observed measurement IDs; retain legal-review status.'))
    findings.append(finding('MAPPING_NOT_MEASUREMENT', 'MEDIUM', 'Heuristic relevance does not establish measured coverage', 'frameworks/crosswalk.json', 'Join mappings to configuration-bound measured evidence before making coverage claims.'))
    if any(row['as_of'] is None for row in rows):
        findings.append(finding('MAPPING_DATE_MISSING', 'MEDIUM', 'Mapping revision time is not established', 'frameworks/crosswalk.json', 'Record the source revision date without replacing it with report generation time.'))
    source_time = date_text(latest.get('ts'))
    if source_time is None:
        findings.append(finding('SOURCE_TIME_MISSING', 'HIGH', 'Measurement snapshot time unavailable', 'latest.json', 'Retain an explicit observed timestamp from the source owner.'))
    elif source_time[:10] > day:
        findings.append(finding('SOURCE_AFTER_REPORT_DAY', 'HIGH', 'Source postdates the report day', 'latest.json', 'Use a contemporaneous source snapshot for historical reporting.'))
    basis = {'version': VERSION, 'day': day, 'sources': provenance}
    report_id = digest(basis)
    return {'schema': VERSION, 'report_id': report_id, 'day': day,
            'brand': 'Council of AI', 'mode': 'READBACK_NOT_REMEASUREMENT',
            'source_as_of': source_time, 'sources': provenance,
            'statistics': {'reported_measured_axes': valid_count(board.get('measured')),
                           'reported_axis_slots': valid_count(board.get('slots')),
                           'catalogue_product_ids': len(product_ids),
                           'unique_heuristic_pairs': len(rows),
                           'mapped_axes': len({r['axis'] for r in rows}),
                           'verified_legal_frameworks': None,
                           'verified_legal_provisions': None,
                           'new_model_measurements': 0},
            'product_ids': product_ids, 'mappings': sorted(rows, key=lambda r: (r['product'], r['axis'])),
            'findings': sorted({f['id']: f for f in findings}.values(), key=lambda f: f['id']),
            'authority': {'execution_authorized': False, 'publication_authorized': False,
                          'human_approval_verified': False, 'legal_certification': False},
            'verification': {'content_digest_available': True, 'signature_state': 'UNSIGNED',
                             'signature_verified': False, 'anchor_verified': False,
                             'independent_measurement_reproduced': False},
            'value_evidence': {'new_valuation': None, 'new_revenue': None,
                               'note': 'Traceable reusable artifacts; not proof of ownership, novelty, customer adoption or increased financial value.'},
            'limitations': ['Counts are readbacks of supplied source data, not independent measurement reproduction.',
                           'Projected inputs retain the observed origin digest separately; the input digest covers the retained projection, not unavailable origin bytes.',
                           'Catalogue identifiers are products; no count of 417 frameworks is established.',
                           'Reports preserve source times and do not retrain models or execute approvals.',
                           'Public legal coverage and signed evidence require their separate owner-controlled qualification.']}


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('output symlink refused')
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def history(out):
    rows = []
    for path in sorted((out / 'reports').glob('*.json')):
        if path.is_symlink() or path.stat().st_size > MAX_BYTES:
            raise ValueError('invalid report history file')
        raw = path.read_bytes()
        report = json.loads(raw)
        if not isinstance(report, dict) or report.get('schema') != VERSION:
            raise ValueError('invalid report history schema')
        rid = digest({'version': VERSION, 'day': report['day'], 'sources': report['sources']})
        if report.get('report_id') != rid or path.name != report['day'] + '-' + rid + '.json':
            raise ValueError('history identity mismatch')
        rows.append({'day': report['day'], 'report_id': rid, 'path': 'reports/' + path.name,
                     'sha256': hashlib.sha256(raw).hexdigest(), 'statistics': report['statistics']})
    return rows


def report_markdown(r, delta):
    s = r['statistics']
    text = ['# Council of AI — Daily evidence readback', '', f"Report day: {r['day']}",
            f"Source snapshot: {r['source_as_of'] or 'UNKNOWN'}", f"Report ID: {r['report_id']}", '',
            '**Readback only. No new model measurement, legal certification or execution authority.**', '',
            f"Source reports {s['reported_measured_axes']} measured axes across {s['reported_axis_slots']} slots.",
            f"Catalogue: {s['catalogue_product_ids']} product IDs; {s['unique_heuristic_pairs']} unique heuristic pairs.",
            'Verified framework/provision coverage: NOT ESTABLISHED.', '', '## Changes', json.dumps(delta, sort_keys=True), '', '## Findings']
    for f in r['findings']:
        text += ['', f"### {f['code']} — {f['severity']}", f['title'], f"Source: `{f['source']}`", f"Acceptance action: {f['next_action']}"]
    text += ['', '## Provenance and limits'] + ['- ' + x for x in r['limitations']]
    return ('\n'.join(text) + '\n').encode()


def render_html(report, timeline, delta, card=None):
    template = Path(__file__).with_name('assurance_template.html').read_text()
    payload = json.dumps({'report': report, 'timeline': timeline, 'delta': delta, 'card': card}, ensure_ascii=True, allow_nan=False, sort_keys=True)
    payload = payload.replace('&', chr(92) + 'u0026').replace('<', chr(92) + 'u003c').replace('>', chr(92) + 'u003e')
    return template.replace('__ASSURANCE_DATA__', payload).encode('utf-8')


def verify(out):
    manifest_path = out / 'manifest.json'
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError('manifest missing or unsafe')
    m = json.loads(manifest_path.read_bytes())
    if m.get('schema') != 'csoai.assurance-manifest/1.0' or m.get('signature_state') != 'UNSIGNED':
        raise ValueError('unexpected manifest schema or signing claim')
    for entry in m['artifacts']:
        rel = Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('artifact path escape')
        p = out / rel
        if p.is_symlink() or not p.resolve().is_relative_to(out.resolve()):
            raise ValueError('unsafe artifact path')
        raw = p.read_bytes()
        if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('artifact digest mismatch: ' + str(rel))
    latest = json.loads((out / 'latest.json').read_bytes())
    card = json.loads((out / 'card.json').read_bytes())
    if latest['report_id'] != m['report_id'] or card['report_id'] != m['report_id']:
        raise ValueError('report identity mismatch')
    if card['report_sha256'] != hashlib.sha256((out / 'latest.json').read_bytes()).hexdigest():
        raise ValueError('card-to-report mismatch')
    history(out)
    return {'status': 'HASHES_VERIFIED', 'artifacts': len(m['artifacts']),
            'report_id': m['report_id'], 'signatures_verified': False,
            'independent_facts_verified': False}


def comparison_delta(current, previous=None):
    delta = {'from_report_id': previous['report_id'] if previous else None,
             'to_report_id': current['report_id'], 'changes': {}}
    if previous:
        for key, value in current['statistics'].items():
            old = previous['statistics'].get(key)
            if old != value:
                delta['changes'][key] = {'before': old, 'after': value}
    return delta


def build(lane, out, day, baseline=None):
    date.fromisoformat(day)
    if out.resolve() == lane.resolve():
        raise ValueError('output must not overwrite the source lane')
    if out.is_symlink():
        raise ValueError('output directory symlink refused')
    report = summarize(lane, day)
    # A generation may be staged in a new directory. Its caller can provide the
    # prior report from an already verified archive without copying that archive.
    if baseline is not None:
        if not isinstance(baseline, dict) or baseline.get('schema') != VERSION:
            raise ValueError('invalid comparison baseline schema')
        expected = digest({'version': VERSION, 'day': baseline['day'], 'sources': baseline['sources']})
        if baseline.get('report_id') != expected or not isinstance(baseline.get('statistics'), dict):
            raise ValueError('invalid comparison baseline identity')
        if baseline['day'] > day or baseline['report_id'] == report['report_id']:
            raise ValueError('comparison baseline must precede the current report')
    out.mkdir(parents=True, exist_ok=True)
    with locked_file(out / '.build.lock'):
        if (out / 'manifest.json').exists():
            verify(out)
        previous = json.loads((out / 'latest.json').read_text()) if (out / 'latest.json').exists() else None
        if baseline is not None:
            if previous is not None and canonical(previous) != canonical(baseline):
                raise ValueError('comparison baseline conflicts with local history')
            previous = baseline
        raw = json.dumps(report, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n'
        rel = 'reports/' + day + '-' + report['report_id'] + '.json'
        target = out / rel
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('immutable report collision')
        atomic_write(target, raw)
        timeline = history(out)
        old_delta_path = out / 'changes.json'
        if previous and previous['report_id'] == report['report_id'] and old_delta_path.exists():
            delta = json.loads(old_delta_path.read_text())
        else:
            delta = comparison_delta(report, previous)
        csv_out = io.StringIO(newline='')
        writer = csv.writer(csv_out)
        writer.writerow(['axis', 'product', 'relevance', 'evidence_status', 'review_state', 'as_of'])
        for r in report['mappings']:
            writer.writerow([r[k] for k in ('axis', 'product', 'relevance', 'evidence_status', 'review_state', 'as_of')])
        card = {'schema': 'csoai.assurance-card/1.0', 'report_id': report['report_id'],
                'report_path': rel, 'report_sha256': hashlib.sha256(raw).hexdigest(),
                'day': day, 'source_as_of': report['source_as_of'],
                'signature_state': 'UNSIGNED', 'signature': None, 'anchor': None,
                'execution_authorized': False, 'measurement_reproduced': False}
        card_raw = canonical(card) + b'\n'
        if len(card_raw) > 3072:
            raise ValueError('compact card exceeds 3 KiB')
        artifacts = {'latest.json': raw, 'card.json': card_raw,
                     'index.json': canonical({'schema': 'csoai.assurance-index/1.0', 'reports': timeline}) + b'\n',
                     'findings.json': canonical({'report_id': report['report_id'], 'findings': report['findings']}) + b'\n',
                     'changes.json': canonical(delta) + b'\n', 'mappings.csv': csv_out.getvalue().encode(),
                     'report.md': report_markdown(report, delta),
                     'index.html': render_html(report, timeline, delta, card)}
        for name, content in artifacts.items():
            atomic_write(out / name, content)
        entries = [{'path': name, 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)} for name, content in sorted(artifacts.items())]
        entries += [{'path': r['path'], 'sha256': r['sha256'], 'bytes': (out / r['path']).stat().st_size} for r in timeline]
        manifest = {'schema': 'csoai.assurance-manifest/1.0', 'report_id': report['report_id'],
                    'signature_state': 'UNSIGNED', 'artifacts': entries}
        atomic_write(out / 'manifest.json', canonical(manifest) + b'\n')
    return verify(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); b.add_argument('--lane', type=Path, required=True); b.add_argument('--out', type=Path, required=True)
    b.add_argument('--date', default=datetime.now(timezone.utc).date().isoformat())
    v = sub.add_parser('verify'); v.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    try:
        result = build(args.lane, args.out, args.date) if args.command == 'build' else verify(args.out)
        print(json.dumps(result, sort_keys=True)); return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'error': str(exc)}), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
