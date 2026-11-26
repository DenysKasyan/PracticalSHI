"""Explainable early warning component C6 and demonstration routing for C7."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

VERSION = 'rules-1.0'
REVIEW = Decimal('45')
PRIORITY = Decimal('60')

def number(data, field, upper=None):
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f'{field}: відсутнє значення')
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f'{field}: очікується число')
    try:
        value = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f'{field}: очікується число') from None
    if not value.is_finite() or value < 0 or (upper is not None and value > upper):
        raise ValueError(f'{field}: поза допустимим діапазоном')
    return value

def checkpoint(data):
    value = data.get('task_completed')
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ('true', 'false'):
        return value.strip().lower() == 'true'
    raise ValueError('task_completed: очікується true або false')

def assess(data):
    """Return score, factors and version, or an explicit unavailable result."""
    try:
        score = number(data, 'test_score', 100)
        progress = number(data, 'course_completion', 100)
        minutes = number(data, 'study_time')
        complete = checkpoint(data)
    except ValueError as error:
        return dict(status='unavailable', risk_score=None, factors={},
                    version=VERSION, reason=str(error))

    raw = {
        'test_score': Decimal('0.40') * (100 - score),
        'course_completion': Decimal('0.35') * (100 - progress),
        'task_completed': Decimal(0 if complete else 15),
        'study_time': Decimal(10) * (1 - min(minutes, Decimal(200)) / 200),
    }
    # Round only the final score used for routing. Keep extra precision in factors.
    index = sum(raw.values()).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return dict(status='ok', risk_score=float(index),
                factors={k: float(v) for k, v in raw.items()},
                version=VERSION, reason=None)

def route(result):
    """C7 maps the score to a queue; a teacher decides on any intervention."""
    if result['status'] != 'ok':
        return 'unavailable'
    score = Decimal(str(result['risk_score']))
    if score >= PRIORITY:
        return 'priority'
    if score >= REVIEW:
        return 'review'
    return 'monitor'
