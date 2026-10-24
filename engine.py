"""Deterministic checks: only configured evidence is cited; never execute input."""

import re
import uuid

SAMPLE = 'Meet EcoVolt, the best energy saver! Get 50% savings on every electricity bill. Guaranteed results. Buy now!!!'
DEFAULT_PROFILE = {
    'name': 'EcoVolt',
    'description': 'Fictional energy technology brand for the TechCircuit demo.',
    'sources': [
        {
            'id': 'VOICE-01',
            'title': 'Voice and style',
            'text': 'Use calm, clear language. Avoid repeated exclamation marks.',
        },
        {
            'id': 'TERM-01',
            'title': 'Approved product name',
            'text': 'Write EcoVolt, not Eco Volt or Eco-Volt.',
        },
        {
            'id': 'CLAIM-01',
            'title': 'Approved energy claim',
            'text': 'Up to 15% energy savings under specified laboratory conditions.',
        },
        {
            'id': 'CLAIM-02',
            'title': 'Promotional language',
            'text': 'Avoid guaranteed results and unsupported best-in-market claims.',
        },
    ],
    'terms': [
        {'term': 'Eco Volt', 'replacement': 'EcoVolt', 'source_id': 'TERM-01'},
        {'term': 'Eco-Volt', 'replacement': 'EcoVolt', 'source_id': 'TERM-01'},
    ],
    'phrases': [
        {
            'phrase': 'guaranteed results',
            'replacement': 'Results may vary',
            'source_id': 'CLAIM-02',
            'severity': 'High',
        },
        {
            'phrase': 'the best',
            'replacement': 'an energy-saving',
            'source_id': 'CLAIM-02',
            'severity': 'Medium',
        },
    ],
    'energy_claim': {
        'source_id': 'CLAIM-01',
        'max_percent': 15,
        'approved_wording': 'up to 15% energy savings under specified laboratory conditions',
    },
    'punctuation_source_id': 'VOICE-01',
}


def validate_profile(profile):
    if (
        not isinstance(profile, dict)
        or not isinstance(profile.get('name'), str)
        or not profile['name'].strip()
    ):
        raise ValueError('A brand name is required.')
    sources = profile.get('sources', [])
    if not isinstance(sources, list) or not sources:
        raise ValueError('Add at least one approved source.')
    if any(
        not isinstance(source, dict)
        or not all(
            isinstance(source.get(field_name), str) and source[field_name].strip()
            for field_name in ('id', 'title', 'text')
        )
        for source in sources
    ):
        raise ValueError('Each source needs an id, title and text.')
    source_ids = [source['id'] for source in sources]
    if len(set(source_ids)) != len(source_ids):
        raise ValueError('Source IDs must be unique.')
    for key, field in [('terms', 'term'), ('phrases', 'phrase')]:
        if not isinstance(profile.get(key, []), list):
            raise ValueError(key + ' must be a list.')
        for rule in profile.get(key, []):
            if (
                not isinstance(rule, dict)
                or not isinstance(rule.get(field), str)
                or not rule[field].strip()
                or not isinstance(rule.get('replacement'), str)
            ):
                raise ValueError(
                    'Rules need a non-empty match and a replacement string.'
                )
            if rule.get('source_id') not in source_ids:
                raise ValueError('Every rule must reference an existing source ID.')
            if key == 'phrases' and rule.get('severity', 'Medium') not in (
                'Low',
                'Medium',
                'High',
            ):
                raise ValueError('Invalid severity.')
    claim = profile.get('energy_claim')
    if claim is not None:
        if (
            not isinstance(claim, dict)
            or claim.get('source_id') not in source_ids
            or not isinstance(claim.get('max_percent'), (int, float))
            or isinstance(claim.get('max_percent'), bool)
            or not 0 <= claim['max_percent'] <= 100
            or not isinstance(claim.get('approved_wording'), str)
            or not claim['approved_wording'].strip()
        ):
            raise ValueError(
                'Energy claim needs a valid source, maximum percent (0–100), and approved wording.'
            )
    if (
        profile.get('punctuation_source_id')
        and profile['punctuation_source_id'] not in source_ids
    ):
        raise ValueError('Invalid punctuation source.')
    return profile


def analyse(text, profile):
    validate_profile(profile)
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Enter content to review.')
    if len(text) > 50000:
        raise ValueError('Limit content to 50,000 characters.')
    sources = {source['id']: source for source in profile['sources']}
    findings = []

    def add_finding(
        kind, severity, match, explanation, source_id=None, suggestion=None
    ):
        findings.append(
            dict(
                id=str(uuid.uuid4()),
                type=kind,
                severity=severity,
                start=match.start(),
                end=match.end(),
                affected=match.group(),
                explanation=explanation,
                source_id=source_id,
                evidence=(
                    sources[source_id]['text']
                    if source_id
                    else 'No approved source found. Human verification required.'
                ),
                suggestion=suggestion,
                status='Open',
            )
        )

    for rules, field, kind, severity in [
        (profile.get('terms', []), 'term', 'Terminology', 'Medium'),
        (profile.get('phrases', []), 'phrase', 'Promotional language', 'High'),
    ]:
        for rule in rules:
            for match in re.finditer(
                r'(?<!\w)' + re.escape(rule[field]) + r'(?!\w)', text, re.I
            ):
                add_finding(
                    kind,
                    rule.get('severity', severity),
                    match,
                    'This wording conflicts with the configured brand guideline.',
                    rule['source_id'],
                    rule['replacement'],
                )
    if profile.get('punctuation_source_id'):
        for match in re.finditer(r'!{2,}', text):
            add_finding(
                'Tone',
                'Low',
                match,
                'Repeated exclamation marks conflict with the approved voice.',
                profile['punctuation_source_id'],
                '!',
            )
    # Keep positions in the original text so findings highlight the correct passage.
    percentage_pattern = re.compile(r'\b\d+(?:\.\d+)?\s*%')
    for sentence in re.finditer(r'(?:[^.!?\n]|(?<=\d)\.(?=\d))+', text):
        sentence_text = sentence.group()
        if not re.search(r'\b(savings?|electricity bills?)\b', sentence_text, re.I):
            continue
        for percentage_match in percentage_pattern.finditer(
            text, sentence.start(), sentence.end()
        ):
            claim = profile.get('energy_claim')
            if not claim:
                add_finding(
                    'Unverified claim',
                    'Medium',
                    percentage_match,
                    'No energy-savings source is configured. This is unverified, not proven false.',
                )
            elif (
                float(percentage_match.group().replace('%', '').strip())
                > claim['max_percent']
            ):
                add_finding(
                    'Claim conflict',
                    'High',
                    percentage_match,
                    'This percentage exceeds the approved energy-savings maximum. Revise the whole claim to preserve its conditions.',
                    claim['source_id'],
                )
            elif not all(
                part in sentence_text.lower()
                for part in ['up to', 'laboratory', 'conditions']
            ) or re.search(r'\b(every|guaranteed|always)\b', sentence_text, re.I):
                add_finding(
                    'Claim qualification',
                    'High',
                    percentage_match,
                    'The percentage needs the approved qualifications and must not imply guaranteed bill savings. Use the approved wording shown below.',
                    claim['source_id'],
                )
    # No evidence: tag superlatives as requiring verification rather than declaring them false.
    for match in re.finditer(
        r'\b(?:number\s*(?:one|1)|100%\s+(?:safe|effective)|clinically proven)\b',
        text,
        re.I,
    ):
        add_finding(
            'Unverified claim',
            'Medium',
            match,
            'Evidence for this statement is not configured. Ask a reviewer to verify it.',
        )
    return sorted(findings, key=lambda finding: finding['start'])


def apply_suggestion(text, finding):
    start, end = finding['start'], finding['end']
    if text[start:end] != finding['affected']:
        raise ValueError('Content changed. Reanalyse before applying this suggestion.')
    if finding.get('suggestion') is None:
        raise ValueError('This finding needs a manual revision.')
    return text[:start] + finding['suggestion'] + text[end:]
