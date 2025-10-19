from django.contrib.auth import login
from django.contrib.auth.models import Group, User
from traceback import format_exc

from Appraise.utils import _get_logger
from Appraise.settings import MIDDLEWARE_LOG_HANDLER

LOGGER = _get_logger(__name__)
# Ensure the middleware log handler is attached once
try:
    handler_attached = any(getattr(h, 'baseFilename', None) == getattr(MIDDLEWARE_LOG_HANDLER, 'baseFilename', None) for h in LOGGER.handlers)
except Exception:
    handler_attached = False
if not handler_attached:
    try:
        LOGGER.addHandler(MIDDLEWARE_LOG_HANDLER)
    except Exception:
        pass


class CrowdeeAuthMiddleware:
    """
    Middleware that looks for a `user_id` query parameter (crowdee user id).
    If present and the current request user is not a superuser, it will:
    - try to find a UserProfile by crowdee_user_id and use the related User
    - if not found, create a new User (username 'user_<id>') and UserProfile
    - ensure the user is added to a default group named 'default'
    - set `user.backend` and call `login(request, user)` so the user is authenticated
    - store `crowdee_user_id`, `param_p`, `task_id` and `hide_ui` in the session so templates can hide UI elements and show status

    This runs after the AuthenticationMiddleware (configured in settings).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            crowdee_user_id = request.GET.get('user_id')
        except Exception:
            crowdee_user_id = None

        # Do nothing for superusers who are already logged in
        if hasattr(request, 'user') and getattr(request.user, 'is_superuser', False):
            return self.get_response(request)

        if crowdee_user_id:
            try:
                from Dashboard.models import UserProfile

                LOGGER.info('CrowdeeAuthMiddleware: processing request. user_id=%s path=%s', crowdee_user_id, getattr(request, 'path', '-'))

                try:
                    profile = UserProfile.objects.get(crowdee_user_id=crowdee_user_id)
                    user = profile.user
                    LOGGER.info('CrowdeeAuthMiddleware: found existing profile for crowdee_user_id=%s (user=%s)', crowdee_user_id, user.username)
                except UserProfile.DoesNotExist:
                    LOGGER.info('CrowdeeAuthMiddleware: no profile found for crowdee_user_id=%s, creating user/profile', crowdee_user_id)
                    # Create a unique username of the form user_<id>
                    base_username = f'user_{crowdee_user_id}'
                    username = base_username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}_{counter}"
                        counter += 1

                    # Create user with unusable password (external auth)
                    user = User.objects.create_user(username=username, password=None)
                    LOGGER.info('CrowdeeAuthMiddleware: created User username=%s id=%s', user.username, user.id)

                    # Create profile linking to crowdee id
                    profile = UserProfile.objects.create(user=user, crowdee_user_id=crowdee_user_id)
                    LOGGER.info('CrowdeeAuthMiddleware: created UserProfile id=%s for user=%s', profile.id, user.username)

                # Ensure default group exists and add user to it
                default_group_name = 'default'
                group, _ = Group.objects.get_or_create(name=default_group_name)
                if not user.groups.filter(name=default_group_name).exists():
                    user.groups.add(group)
                    LOGGER.info('CrowdeeAuthMiddleware: added user %s to group "%s"', user.username, default_group_name)
                else:
                    LOGGER.debug('CrowdeeAuthMiddleware: user %s already in group "%s"', user.username, default_group_name)

                # Mark backend so Django can log the user in without authenticate()
                try:
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, user)
                    LOGGER.info('CrowdeeAuthMiddleware: logged in user %s (crowdee_user_id=%s)', user.username, crowdee_user_id)
                except Exception:
                    LOGGER.error('CrowdeeAuthMiddleware: failed to login user %s for crowdee_user_id=%s; traceback=%s', getattr(user, 'username', None), crowdee_user_id, format_exc())

                # Persist crowdee id and hide flag in session so templates can use them across requests
                try:
                    # Save crowdee id
                    request.session['crowdee_user_id'] = str(crowdee_user_id)
                    # Save optional task info if present in GET
                    param_p = request.GET.get('param_p')
                    task_id = request.GET.get('task_id')
                    if param_p is not None:
                        request.session['param_p'] = str(param_p)
                    if task_id is not None:
                        request.session['task_id'] = str(task_id)

                    request.session['hide_ui'] = True
                    request.session.modified = True
                    LOGGER.info('CrowdeeAuthMiddleware: persisted session keys for crowdee_user_id=%s param_p=%s task_id=%s', crowdee_user_id, request.session.get('param_p'), request.session.get('task_id'))
                except Exception:
                    LOGGER.error('CrowdeeAuthMiddleware: failed to persist session for crowdee_user_id=%s; traceback=%s', crowdee_user_id, format_exc())

            except Exception:
                # Log exception with traceback so debugging is easier
                try:
                    LOGGER.exception('CrowdeeAuthMiddleware: unexpected error when processing crowdee_user_id=%s: %s', crowdee_user_id, format_exc())
                except Exception:
                    # last-resort print
                    print('CrowdeeAuthMiddleware: logging failed', crowdee_user_id)
                    print(format_exc())

        response = self.get_response(request)
        return response
