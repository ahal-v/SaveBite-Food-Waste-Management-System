// ── Mobile Nav Toggle ──────────────────────────────────────────────────────
const navToggle = document.getElementById('navToggle');
const navLinks  = document.querySelector('.nav-links');
if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => navLinks.classList.toggle('open'));
    document.addEventListener('click', e => {
        if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
            navLinks.classList.remove('open');
        }
    });
}

// ── Auto-dismiss Flash Messages ────────────────────────────────────────────
document.querySelectorAll('.flash').forEach(flash => {
    setTimeout(() => {
        flash.style.transition = 'opacity 0.5s, transform 0.5s';
        flash.style.opacity = '0';
        flash.style.transform = 'translateX(30px)';
        setTimeout(() => flash.remove(), 500);
    }, 4000);
});

// ── Confirm on Forms with data-confirm ─────────────────────────────────────
document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
        if (!confirm(form.dataset.confirm)) e.preventDefault();
    });
});

// ── Animate stat cards on scroll (Intersection Observer) ──────────────────
const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animation = 'fadeInUp 0.4s ease forwards';
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.stat-card, .card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    observer.observe(el);
});

// Inject keyframe animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);
