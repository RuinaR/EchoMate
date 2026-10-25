"""Public command shape. Remote metadata is evidence, never an approval."""
COMMAND_ACCESS={'동의':'self_ephemeral','성격':'owner_ephemeral'}
PRETRAINED_COMMAND_ACCESS={'동의':'self_ephemeral','캐릭터':'public_ephemeral'}

def command_access(mode='legacy'):
    if mode=='legacy':return dict(COMMAND_ACCESS)
    if mode=='pretrained':return dict(PRETRAINED_COMMAND_ACCESS)
    raise ValueError('Unknown command contract')

def rows(commands,application,guild=None):
    result=[]
    for command in commands:
        # Preserve wire arrays: discord.py 2.7.1 AppCommand's ArrayFlags
        # conversion shifts zero-based context/install values and loses [0].
        if int(command['application_id'])!=application:raise ValueError('Wrong application')
        scope=command.get('guild_id')
        if scope is not None and int(scope)!=guild:raise ValueError('Wrong command scope')
        contexts=command.get('contexts');installs=command.get('integration_types')
        for values in (contexts,installs):
            if values is not None and (not isinstance(values,list) or any(type(v) is not int or v<0 for v in values)):
                raise ValueError('Invalid command access metadata')
        permissions=command.get('default_member_permissions')
        result.append(dict(id=str(int(command['id'])),name=command['name'],type=command.get('type',1),
            contexts=sorted(set(contexts)) if contexts is not None else None,
            integration_types=sorted(set(installs)) if installs is not None else None,
            default_member_permissions=str(int(permissions)) if permissions is not None else None,
            nsfw=bool(command.get('nsfw',False))))
    return sorted(result,key=lambda row:row['id'])


def consent_contract(commands,*,mode='legacy'):
    """Require the complete guild-installed slash set, without an admin gate.

    Server permission overrides and actual client visibility need separate checks.
    Missing remote context fields are unknown, not proof of the intended scope.
    """
    access=command_access(mode)
    return (len(commands)==len(access) and {c['name'] for c in commands}==set(access)
        and all(c['type']==1 and c.get('contexts')==[0] and c.get('integration_types')==[0]
            and c.get('default_member_permissions') is None and not c.get('nsfw',False) for c in commands))


def failure_details(exc,stage):
    # Never persist exception text, raw SQL/HTTP payload, or Authorization values.
    return dict(status='cancelled' if isinstance(exc,BaseException) and type(exc).__name__=='CancelledError' else 'failed',
        stage=stage,error=type(exc).__name__,http_status=getattr(exc,'status',None),discord_code=getattr(exc,'code',None))
