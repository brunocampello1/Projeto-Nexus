// Drag and drop para reordenação de tarefas
document.addEventListener('DOMContentLoaded', () => {
    const list = document.getElementById('tasks-list');
    if (!list) return;

    let dragging = null;
    const placeholder = document.createElement('div');
    placeholder.className = 'drag-placeholder';

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.task-card:not(.dragging):not(.drag-placeholder)')];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > (closest.offset || -Infinity)) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: -Infinity }).element;
    }

    list.addEventListener('dragstart', (e) => {
        const target = e.target.closest('.task-card');
        if (!target) return;
        dragging = target;
        target.classList.add('dragging');
        // define transfer to allow DnD
        e.dataTransfer.effectAllowed = 'move';
        try { e.dataTransfer.setData('text/plain', target.dataset.id); } catch (e) { /* IE/edge */ }
        // seta placeholder height
        placeholder.style.height = `${target.getBoundingClientRect().height}px`;
    });

    list.addEventListener('dragend', async (e) => {
        if (!dragging) return;
        dragging.classList.remove('dragging');
        // coloca de volta onde placeholder estava
        if (placeholder.parentNode) {
            placeholder.parentNode.replaceChild(dragging, placeholder);
        }
        dragging = null;

        // Salvar nova ordem
        await persistOrder();
    });

    list.addEventListener('dragover', (e) => {
        e.preventDefault();
        const afterElement = getDragAfterElement(list, e.clientY);
        if (!afterElement) {
            if (list.lastElementChild !== placeholder) {
                list.appendChild(placeholder);
            }
        } else {
            if (afterElement !== placeholder) {
                list.insertBefore(placeholder, afterElement);
            }
        }
    });

    list.addEventListener('drop', (e) => {
        e.preventDefault();
        // noop - dragend tratará a substituição
    });

    async function persistOrder() {
        const ids = [...list.querySelectorAll('.task-card')].map(el => parseInt(el.dataset.id, 10));
        try {
            const res = await fetch('/reorder_tarefas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order: ids })
            });
            if (!res.ok) throw new Error('Falha ao salvar ordem');
        } catch (err) {
            console.error(err);
        }
    }
});
