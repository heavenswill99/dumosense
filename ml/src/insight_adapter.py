"""Backend integration boundary for the documented MindGuard insight contract.

This does not authenticate HTTP requests. The backend must establish identity and
check current consent before calling. Experimental alerts are deliberately not
published by this adapter; it emits descriptive session/baseline information.
"""
from hashlib import sha256

def build_insight(record, *, authenticated_user_id, consent_verified):
    if not authenticated_user_id or authenticated_user_id != record.get('user_id'):
        raise PermissionError('Session does not belong to authenticated user')
    if consent_verified is not True:
        raise PermissionError('Current cognitive-processing consent required')
    for field in ['run_id','session_id','model_version','index_time','current_performance','baselines']:
        if field not in record:
            raise ValueError('Missing record field: '+field)
    accuracy=record['current_performance'].get('accuracy')
    if accuracy is None or not 0 <= accuracy <= 1:
        raise ValueError('Invalid current accuracy')
    baseline=record['baselines'].get('per_domain',{})
    available=baseline.get('z') is not None
    identity='|'.join(str(record[k]) for k in ['user_id','session_id','model_version','run_id'])
    text=f'This session accuracy was {accuracy:.1%}.'
    if available:
        text+=f" Your prior same-domain median was {baseline['median']:.1%} across {baseline['n_valid']} sessions."
    else:
        text+=' A reliable same-domain comparison is not available for this session.'
    return dict(product_code='MINDGUARD',insight_id='INS-'+sha256(identity.encode()).hexdigest()[:24],
       insight=dict(insight_type='session_summary' if available else 'insufficient_data',priority='low',text=text,
                    explanation='A descriptive performance comparison, not a medical assessment or a validated change alert.'),
       recommendation=dict(recommendation_type='maintain_monitoring',text='Continue your usual assessment schedule.',priority='low'),
       traceability=dict(run_id=record['run_id'],model_version=record['model_version'],session_id=record['session_id'],
                         index_time=record['index_time'],history_end=baseline.get('ts_max_prior')),
       delivery=dict(automatic_alert=False,clinical_claim=False))
