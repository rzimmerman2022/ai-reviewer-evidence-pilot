"""Synthetic regression cases. No provider calls, keys or client content."""
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sda_semantic_review import (MODEL,ENDPOINT,ReviewError,unit,prepare,assess,execute,digest,validate_response)
from sda_semantic_profiles import questions

def plan(text='The analyst owned the audit process.', **kwargs):
    evidence=[unit('original',text,'S1','a'*64,'paragraph 1'),
              unit('proposal','The analyst owned the audit process.','P1','b'*64,'claim 1')]
    return prepare(domain='fixture',purpose='evidence_integration',subject_id='synthetic',basis_sha256='c'*64,
                   units=evidence,questions=questions('evidence_integration','claim',['original','proposal'],checks=['claim_support']),
                   expected_subject_ids=['claim'],classification='synthetic',**kwargs)

def response(payload):
    answers={}
    for ident,q in payload['questions'].items():
        labels=list(q['criteria']);probs={label:float(i==0) for i,label in enumerate(labels)}
        answers[ident]={'type':'choice','choice':labels[0],'probabilities':probs,'confidence':1.0}
    return {'model':MODEL,'answers':answers,'usage':{'input_tokens':1200,'output_tokens':45}}

def retained(p):
    return {r['id']:{'request':r['payload'],'request_sha256':r['request_sha256'],'response':response(r['payload'])} for r in p['requests']}

def config(runtime):
    return {'schema':'sda-jev-run-config-1','enabled':True,'endpoint':ENDPOINT,'model':MODEL,
            'allowed_data_classes':['synthetic'],'authorization_reference':'synthetic-test','account_reference':'fixture',
            'auto_recharge':False,'expires_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),
            'max_cost_usd':'0.01','max_requests':3,'price_per_million_input_usd':'0.042',
            'run_id':'synthetic-run','runtime_directory':str(runtime.resolve())}

def test_changed_evidence_cannot_rebind_prior_judgment():
    before=plan();after=plan('The analyst never owned an audit.')
    with pytest.raises(ReviewError,match='different evidence'):assess(after,retained(before))
    result=assess(before,retained(before))
    assert result['state']=='REVIEW_REQUIRED' and not result['release_authorized'] and not result['client_approval_inferred']

def test_missing_answers_remain_unassessed():
    result=assess(plan(),{})
    assert result['state']=='PARTIAL_REVIEW_REQUIRED' and result['not_evaluated'][0]['reason']=='NO_RESPONSE'

def test_stale_or_incomplete_input_is_not_negative_evidence():
    p=plan();args={k:p[k] for k in ('domain','purpose','subject_id','basis_sha256','units','questions','expected_subject_ids','classification')}
    args['units'][0]['complete']=False
    value=prepare(**args)
    assert not value['requests'] and value['not_evaluated'][0]['reason']=='STALE_OR_INCOMPLETE_EVIDENCE'

def test_coverage_cannot_silently_drop_occupation():
    p=plan();args={k:p[k] for k in ('domain','purpose','subject_id','basis_sha256','units','questions','classification')}
    with pytest.raises(ReviewError,match='Unaccounted'):prepare(**args,expected_subject_ids=['claim','alternative'])
    explicit=prepare(**args,expected_subject_ids=['claim','alternative'],exclusions={'alternative':'Missing original descriptor; obtain before conclusion'})
    assert assess(explicit,retained(explicit))['state']=='PARTIAL_REVIEW_REQUIRED'

@pytest.mark.parametrize('change',[lambda r:r.update(model='jev-latest'),lambda r:r['answers'].clear(),
 lambda r:r['usage'].update(input_tokens=64001),lambda r:next(iter(r['answers'].values())).update(confidence=.1),
 lambda r:next(iter(r['answers'].values()))['probabilities'].update(SUPPORTED=float('nan')),
 lambda r:next(iter(r['answers'].values())).update(choice='unlisted')])
def test_malformed_provider_result_refused(change):
    payload=plan()['requests'][0]['payload'];r=response(payload);change(r)
    with pytest.raises(ReviewError):validate_response(payload,r)

def test_live_two_decimal_confidence_is_retained_without_relaxing_material_checks():
    payload={'model':MODEL,'questions':{'q':{'type':'choice','criteria':{'concern':'','clear':'','unknown':''}}}}
    r={'model':MODEL,'answers':{'q':{'type':'choice','choice':'concern','confidence':.51,
       'probabilities':{'concern':.67,'clear':.33,'unknown':0.0}}},'usage':{'input_tokens':647,'output_tokens':61}}
    assert validate_response(payload,r) is r
    r['answers']['q']['confidence']=.60
    with pytest.raises(ReviewError,match='confidence'):validate_response(payload,r)
    r['answers']['q']['confidence']=.51
    r['answers']['q']['probabilities']['clear']=.34
    with pytest.raises(ReviewError,match='confidence'):validate_response(payload,r)
    r['answers']['q']['probabilities']['clear']=.20
    with pytest.raises(ReviewError,match='distribution'):validate_response(payload,r)

def test_rounded_distribution_can_sum_to_point_ninety_nine():
    payload={'model':MODEL,'questions':{'q':{'type':'choice','criteria':{'a':'','b':'','c':''}}}}
    r={'model':MODEL,'answers':{'q':{'type':'choice','choice':'a','confidence':0,
       'probabilities':{'a':.33,'b':.33,'c':.33}}},'usage':{'input_tokens':100,'output_tokens':40}}
    assert validate_response(payload,r) is r

@pytest.mark.parametrize('score',[-.23,.23,9.01])
def test_score_rounding_still_requires_feasible_unit_probability_mass(score):
    levels=[str(i) for i in range(10)]
    payload={'model':MODEL,'questions':{'q':{'type':'score','criteria':levels}}}
    r={'model':MODEL,'answers':{'q':{'type':'score','score':score,'confidence':1,
       'legend':dict(enumerate(levels)), 'probabilities':{str(i):float(i==0) for i in range(10)}}},
       'usage':{'input_tokens':100,'output_tokens':40}}
    r['answers']['q']['legend']={str(i):v for i,v in enumerate(levels)}
    with pytest.raises(ReviewError,match='Score'):validate_response(payload,r)

def test_score_accepts_rounded_provider_example():
    payload={'model':MODEL,'questions':{'q':{'type':'score','criteria':['low','medium','high']}}}
    r={'model':MODEL,'answers':{'q':{'type':'score','score':1.43,'confidence':.35,
       'legend':{'0':'low','1':'medium','2':'high'},'probabilities':{'0':0,'1':.57,'2':.43}}},
       'usage':{'input_tokens':100,'output_tokens':40}}
    assert validate_response(payload,r) is r

def test_criteria_order_changes_identity():
    p=plan();q=copy.deepcopy(p['questions']);q[0]['question']['criteria']=dict(reversed(list(q[0]['question']['criteria'].items())))
    args={k:p[k] for k in ('domain','purpose','subject_id','basis_sha256','units','expected_subject_ids','classification')}
    reordered=prepare(**args,questions=q)
    assert p['requests'][0]['request_sha256']!=reordered['requests'][0]['request_sha256']

def test_execution_reuses_identical_request_and_never_grants_authority(tmp_path):
    calls=[]
    def provider(payload,key):calls.append(payload);return response(payload)
    p=plan();c=config(tmp_path)
    one=execute(p,c,tmp_path,call=provider);two=execute(p,c,tmp_path,call=provider)
    assert len(calls)==1 and one==two
    assert not two['assessment']['release_authorized']

def test_failed_attempt_reserved_and_not_retried(tmp_path):
    calls=[];c=config(tmp_path)
    def provider(*args):calls.append(1);raise ReviewError('fixture transport error')
    with pytest.raises(ReviewError):execute(plan(),c,tmp_path,call=provider)
    with pytest.raises(ReviewError,match='uncertain outcome'):execute(plan(),c,tmp_path,call=provider)
    assert len(calls)==1

def test_budget_is_cumulative_and_bound_to_runtime(tmp_path):
    c=config(tmp_path);c['max_cost_usd']='0.002688';calls=[]
    def provider(payload,key):calls.append(1);return response(payload)
    execute(plan(),c,tmp_path,call=provider)
    with pytest.raises(ReviewError,match='budget exhausted'):execute(plan('Different source'),c,tmp_path,call=provider)
    with pytest.raises(ReviewError,match='budget directory'):execute(plan(),c,tmp_path/'another',call=provider)
    assert len(calls)==1

def test_private_data_not_authorized_by_public_pilot(tmp_path):
    p=plan();args={k:p[k] for k in ('domain','purpose','subject_id','basis_sha256','units','questions','expected_subject_ids')}
    private=prepare(**args,classification='private_client')
    with pytest.raises(ReviewError,match='Data class'):execute(private,config(tmp_path),tmp_path)
    assert not list(tmp_path.glob('reservation-*'))

def test_forged_cache_cannot_substitute_other_request(tmp_path):
    p=plan();c=config(tmp_path);execute(p,c,tmp_path,call=lambda p,k:response(p))
    path=next(tmp_path.glob('response-*'));v=json.loads(path.read_text());v['request']=plan('Changed')['requests'][0]['payload'];path.write_text(json.dumps(v))
    with pytest.raises(ReviewError,match='binding changed'):execute(p,c,tmp_path,call=lambda p,k:response(p))


def test_oversized_evidence_is_explicitly_unevaluated_not_truncated():
    p=plan('Evidence. '*5000)
    assert not p['requests'] and p['not_evaluated'][0]['reason']=='SCOPE_EXCEEDS_BOUNDED_CONTEXT'
    assert len(p['units'][0]['text'])==50000
    assert assess(p,{})['state']=='PARTIAL_REVIEW_REQUIRED'


def test_missing_credential_never_reserves_or_creates_runtime(tmp_path):
    runtime=tmp_path/'not-created'
    with pytest.raises(ReviewError,match='Credential'):execute(plan(),config(runtime),runtime)
    assert not runtime.exists()


def test_frozen_synthetic_pilot_has_blinded_labels_and_bounded_count():
    from sda_semantic_pilot import build,score
    p,expected,meta=build()
    assert len(p['requests'])==60 and not p['not_evaluated']
    assert all('expected' not in r['payload']['state'] for r in p['requests'])
    result=score({})
    assert result['completed']==0 and result['correct']==0 and result['matched_pairs_correct']==0
    assert not result['release_authorized']
