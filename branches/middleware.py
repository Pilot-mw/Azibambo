from .models import Branch


class BranchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = request.user.profile
            is_admin = profile.role == 'super_admin'

            if 'active_branch' not in request.session:
                if profile.branch:
                    request.session['active_branch'] = profile.branch_id
                elif is_admin:
                    first_branch = Branch.objects.filter(is_active=True).first()
                    if first_branch:
                        request.session['active_branch'] = first_branch.id
                elif profile.role == 'manager':
                    managed = Branch.objects.filter(manager=request.user, is_active=True).first()
                    if managed:
                        request.session['active_branch'] = managed.id

            active_id = request.session.get('active_branch')
            if active_id:
                try:
                    request.current_branch = Branch.objects.get(id=active_id, is_active=True)
                except Branch.DoesNotExist:
                    request.current_branch = None
                    if 'active_branch' in request.session:
                        del request.session['active_branch']
            else:
                request.current_branch = None

            if request.current_branch:
                self._enforce_branch_restriction(request)

        return self.get_response(request)

    def _enforce_branch_restriction(self, request):
        profile = request.user.profile
        if profile.role == 'cashier' and profile.branch:
            if request.current_branch.id != profile.branch_id:
                request.session['active_branch'] = profile.branch_id
                try:
                    request.current_branch = Branch.objects.get(id=profile.branch_id)
                except Branch.DoesNotExist:
                    request.current_branch = None
