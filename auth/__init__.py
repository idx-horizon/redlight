from functools import wraps
from flask import session, redirect, url_for, abort, current_app, request
from flask_login import current_user

def requires_permission():
    """
    Enforces RBAC based on the current route's blueprint and view name.
    Uses current_user.can_access() which supports:
      - wildcard '*'
      - deny overrides
      - role + user permissions
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):

            # Must be logged in
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()

            # Extract blueprint and view from endpoint
            # endpoint format: "blueprint.view_func"
            endpoint = request.endpoint or ""

            if "." in endpoint:
                blueprint, view = endpoint.split(".", 1)
            else:
                blueprint = "main"
                view = endpoint

            # Check permission
            if not current_user.can_access(blueprint, view):
                abort(403)

            return f(*args, **kwargs)

        return wrapped
    return decorator

