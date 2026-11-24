"""Expose the originating message snapshot to the running maid, not as authorization."""


import secrets


def describe_origin(driver, event):
    if driver is None:
        return {'status': 'unavailable', 'reason': 'maid_session_not_found',
                'hint': 'Invoke the tool from an active maid task.'}
    current = getattr(driver, '_child_event', None)
    if current is None:
        return {'status': 'unavailable', 'reason': 'maid_execution_not_running'}
    if current is not event:
        expected = getattr(current, '_maid_run_token', None)
        supplied = getattr(event, '_maid_run_token', None)
        if not (isinstance(expected, str) and isinstance(supplied, str)
                and expected and secrets.compare_digest(expected, supplied)
                and getattr(current, '_maid_session_id', None) == getattr(event, '_maid_session_id', None)):
            return {'status': 'unavailable', 'reason': 'maid_event_mismatch',
                    'hint': 'The caller event is not bound to this maid execution.'}
    execution = getattr(driver, 'current_execution', None) or {}
    identity = execution.get('origin_identity')
    if not execution.get('task_id') or not isinstance(identity, dict):
        return {'status': 'unavailable', 'reason': 'no_task_origin'}
    sender = identity.get('senderId')
    platform = identity.get('platformName')
    message = identity.get('sourceMessageId')
    if not isinstance(sender, str) or not sender.strip():
        return {'status': 'unavailable', 'reason': 'original_sender_missing',
                'hint': 'Start a new task from a platform message.'}
    sender = sender.strip()
    has_message = isinstance(message, str) and bool(message.strip())
    platform = platform if isinstance(platform, str) else ''
    # OneBot's sender ID is the QQ account ID; official QQ adapters can use openid.
    qq_number = sender if platform.lower() == 'aiocqhttp' and sender.isascii() and sender.isdigit() else None
    return {
        'status': 'ok' if has_message else 'partial', 'scope': 'original_message_for_current_task_execution',
        'task_id': str(execution['task_id']),
        'platform_name': platform,
        'platform_id': identity.get('platformId') or None,
        'sender_id': sender, 'qq_number': qq_number,
        'original_message_id': message if has_message else None,
        'is_astrbot_admin': identity.get('role') == 'admin' and identity.get('apiAdminAllowed') is True,
        'identity_complete': has_message,
        'notice': 'Local snapshot of the original dispatch, not a signed remote authorization; '
                  'additional messages are separate inputs and this is not their message ID.',
    }
