"""Atomic advisory rubrics shared by evidence-led domain adapters."""
VERSION = 'sda-semantic-profiles-1'

RELATIONS = {
    'SUPPORTED': 'The supplied source context supports the proposition at its stated scope and attribution.',
    'PARTIAL': 'Some support exists, but a material qualifier, ownership limit or condition is missing.',
    'CONTRADICTED': 'Supplied evidence directly conflicts with the proposition.',
    'NOT_ESTABLISHED': 'The supplied evidence does not establish the proposition; this is not proof it is false.',
    'INSUFFICIENT_EVIDENCE': 'Relevant source text or contextual information is missing or cannot resolve the question.',
}
CONCERNS = {
    'CONCERN_PRESENT': 'A concrete issue against the named criterion is present in the supplied text.',
    'NO_CONCERN_FOUND': 'No issue against this narrow criterion is apparent in the supplied text; this is not overall approval.',
    'INSUFFICIENT_EVIDENCE': 'Supplied material does not allow this criterion to be assessed.',
}
PURPOSES = {
    'intake': {
        'known_answer': 'Does the proposed question request information already explicitly established in the supplied evidence?',
        'decision_use': 'Does the proposed question lack a concrete link to a named engagement decision or promised outcome?',
    },
    'spd': {
        'inventory_completeness': 'Does the complete source contain a material role, employer, education, credential, project or capability omitted from the supplied discovery inventory? Identify the specific omission; counts alone do not establish coverage.',
        'answer_interpretation': 'Does the proposed interpretation of the exact question and answer omit a qualifier, ownership limit, uncertainty or stated preference?',
        'discovery_coverage': 'Does the proposed discovery decision dismiss a material source item without a supported reason or useful follow-up?',
    },
    'evidence_integration': {
        'claim_support': 'Does source evidence support the proposed claim? Preserve personal versus team ownership, approximate quantities, chronology and planned versus completed work.',
        'correction_precedence': 'Does the proposed interpretation conflict with a later explicit correction, or treat quoted/model-proposed text as accepted biography?',
    },
    'market_mapping': {
        'functional_transfer': 'Does supplied duty/task evidence support the proposed transfer mechanism rather than merely sharing a job title or broad vocabulary?',
        'formal_eligibility': 'Does supplied client and employer evidence establish the stated formal eligibility proposition? Occupational similarities cannot establish credentials or substitution policies.',
        'market_feasibility': 'Does the stated market interpretation respect supplied geography, source/sample and time limitations? Do not calculate numeric thresholds.',
        'client_priorities': 'Does the proposed route conflict with explicit client preferences or constraints? Do not infer willingness to trade pay or location from distress.',
    },
    'strategy': {
        'functional_transfer': 'Does supplied evidence support the proposed transfer mechanism at its actual scope?',
        'formal_eligibility': 'Does the evidence establish the proposed eligibility proposition independently of transferable skills?',
        'market_feasibility': 'Does the recommendation overgeneralize the supplied market sample, confuse industry and occupation, or turn projections into individual hiring odds?',
        'client_priorities': 'Does the recommendation conflict with the client stated priorities, including desired ownership and level?',
        'missed_value': 'Does the proposed recommendation omit a materially relevant supported capability or credible competing route identified in the supplied evidence?',
    },
    'deliverable_review': {
        'claim_support': 'Does source context support the proposed client-facing claim without invented scale, seniority, impact or credentials?',
        'missed_value': 'Does this content omit the strongest relevant supported value needed for its stated reader and purpose?',
        'client_constraints': 'Does this advice or wording conflict with the supplied client constraints, accepted scope or current strategy?',
        'positioning_and_proof': 'Does the copy rely on generic positioning without the relevant supplied concrete proof?',
        'concise_plain_copy': 'Does the copy contain avoidable repetition, unsupported praise, marketing filler or jargon that adds no useful meaning? Length alone is not a defect.',
        'task_usability': 'Does the content leave the client unable to perform the promised task or omit essential tailoring/use instructions? Do not judge visual appearance from text.',
    },
    'advisory': {
        'claim_support': 'Does the cited original support the proposed claim while preserving observed record, attributed statement and interpretation as distinct?',
        'missed_value': 'Does the proposed analysis omit material supplied counterevidence or an applicable competing explanation?',
        'client_constraints': 'Does the proposed recommendation conflict with the accepted objective, authority, baseline or explicit constraints?',
    },
}
RELATION_KEYS = {'claim_support', 'functional_transfer', 'formal_eligibility'}


def questions(purpose, subject_id, evidence_ids, *, checks=None):
    if purpose not in PURPOSES:
        raise ValueError('Unknown semantic purpose')
    chosen = list(PURPOSES[purpose]) if checks is None else checks
    if not chosen or len(chosen) != len(set(chosen)) or not set(chosen) <= set(PURPOSES[purpose]):
        raise ValueError('Unknown or duplicate rubric checks')
    return [{'id': subject_id + '/' + check, 'subject_ids': [subject_id], 'evidence_ids': evidence_ids,
             'rubric_id': VERSION + '/' + purpose + '/' + check,
             'question': {'type': 'choice', 'instructions': PURPOSES[purpose][check],
                          'criteria': dict(RELATIONS if check in RELATION_KEYS else CONCERNS)}} for check in chosen]
