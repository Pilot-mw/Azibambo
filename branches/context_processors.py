from .models import Branch


def _theme_dict(branch=None):
    if branch:
        return {
            'primary': branch.theme_color,
            'secondary': branch.secondary_color,
            'logo_bg': branch.logo_background_color,
            'mode': branch.theme_mode,
            'sidebar_bg': branch.sidebar_bg,
            'sidebar_text': branch.sidebar_text,
            'header_bg': branch.header_bg,
            'header_text': branch.header_text,
            'selection_bg': branch.selection_bg,
            'selection_text': branch.selection_text,
            'button_color': branch.button_color,
            'card_accent': branch.card_accent,
            'widget_bg': branch.widget_bg,
        }
    return {
        'primary': '#2563eb',
        'secondary': '#1d4ed8',
        'logo_bg': '#1e293b',
        'mode': 'dark',
        'sidebar_bg': '#1e293b',
        'sidebar_text': '#cbd5e1',
        'header_bg': '#2563eb',
        'header_text': '#ffffff',
        'selection_bg': '#2563eb',
        'selection_text': '#ffffff',
        'button_color': '#2563eb',
        'card_accent': '#2563eb',
        'widget_bg': '#16213e',
    }


def branch_context(request):
    ctx = {
        'all_branches': [],
        'current_branch': None,
        'branch_theme': {},
    }
    if request.user.is_authenticated:
        profile = request.user.profile
        if profile.role == 'super_admin':
            ctx['all_branches'] = Branch.objects.filter(is_active=True)
        else:
            user_branches = []
            if profile.branch:
                user_branches.append(profile.branch_id)
            if profile.role == 'manager':
                for b in Branch.objects.filter(manager=request.user, is_active=True):
                    if b.id not in user_branches:
                        user_branches.append(b.id)
            ctx['all_branches'] = Branch.objects.filter(id__in=user_branches, is_active=True) if user_branches else Branch.objects.none()
        current = getattr(request, 'current_branch', None)
        ctx['current_branch'] = current
        ctx['branch_theme'] = _theme_dict(current)
    return ctx
