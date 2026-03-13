
from flask_login import current_user

def get_sidebar_items():
    """
    Returns a dict of blueprints and views the current_user can access.
    Only include items the user can actually access.
    """
    items = {
        'admin': ['dashboard','logs'],
        'personal': ['alcohol','finance','countdown'],
        'runner': ['runs','compare','dashboard'],
        'parkrun': ['viewmap','events','cancellations', 'dashboard','difficulty','mostevents','countries'],
        'Transactions': ['dashboard']
    }

    # Filter based on current_user permissions
    if not current_user.is_authenticated:
        return {}  # no access for anonymous users

    return {bp: [v for v in views if current_user.can_access(bp, v)]
            for bp, views in items.items()}
