document.addEventListener('DOMContentLoaded', () => {
    
    // --- Form Handlers ---
    document.addEventListener('submit', async (e) => {
        const form = e.target;
        if (!form.classList.contains('ajax-form')) return;

        const isHabito = form.classList.contains('form-add-habito') ||
                         form.classList.contains('form-delete-habito');
        
        if (!isHabito) return;
        
        e.preventDefault();

        const btn = form.querySelector('button[type="submit"]');
        let originalHtml = '';
        if (btn && form.classList.contains('form-add-habito')) {
            originalHtml = btn.innerHTML;
            btn.innerHTML = '...';
            btn.disabled = true;
        }

        try {
            const response = await fetch(form.action, {
                method: form.method,
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (!response.ok) throw new Error('Network error');

            const data = await response.json();
            if (data.success) {
                
                if (form.classList.contains('form-add-habito')) {
                    // Re-navigate via SPA to refresh the habit table
                    // (building the full row client-side would require week_offset context)
                    if (typeof navigateSPA === 'function') {
                        await navigateSPA(window.location.href);
                    } else {
                        window.location.reload();
                    }
                }
                else if (form.classList.contains('form-delete-habito')) {
                    const tr = form.closest('tr');
                    if (tr) tr.remove();
                    
                    const tbody = document.querySelector('.habits-table tbody');
                    if (tbody && tbody.children.length === 0) {
                        const tableContainer = document.querySelector('.habits-table-container');
                        tableContainer.innerHTML = `<div style="padding: 1.5rem; text-align: center; color: var(--text-secondary); font-size: 0.9rem;">
                            Nenhum hábito cadastrado ainda. Adicione seu primeiro hábito acima!
                        </div>`;
                    }
                }
            }
        } catch (error) {
            console.error(error);
        } finally {
            if (btn && document.body.contains(btn) && form.classList.contains('form-add-habito')) {
                btn.innerHTML = originalHtml;
                btn.disabled = false;
            }
        }
    });
});
