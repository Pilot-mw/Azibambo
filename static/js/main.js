document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.querySelector('.toggle-sidebar');
    const sidebar = document.querySelector('.sidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 992 && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }

    document.querySelectorAll('.alert-dismiss').forEach(function(btn) {
        btn.addEventListener('click', function() {
            this.closest('.alert').style.display = 'none';
        });
    });

    setTimeout(function() {
        document.querySelectorAll('.alert').forEach(function(alert) {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(function() { alert.style.display = 'none'; }, 500);
        });
    }, 5000);

    const activeLink = document.querySelector('.sidebar-menu a[href="' + window.location.pathname + '"]');
    if (activeLink) activeLink.classList.add('active');

    document.querySelectorAll('.sidebar-menu a').forEach(function(link) {
        link.addEventListener('click', function() {
            document.querySelectorAll('.sidebar-menu a').forEach(function(l) { l.classList.remove('active'); });
            this.classList.add('active');
        });
    });
});

function formatNumber(num) {
    return new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
}

function formatCurrency(num) {
    return 'MK ' + formatNumber(num);
}
