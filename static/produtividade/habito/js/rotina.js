document.addEventListener('DOMContentLoaded', () => {
    const plannerGrid = document.getElementById('plannerGrid');
    const blocks = document.querySelectorAll('.routine-block');
    
    // Modal elements
    const editModal = document.getElementById('editModal');
    const formEdit = document.getElementById('formEditItem');
    const inputId = document.getElementById('editItemId');
    const inputNome = document.getElementById('editHabitoNome');
    const inputInicio = document.getElementById('editHorarioInicio');
    const inputFim = document.getElementById('editHorarioFim');
    const inputIsBloqueio = document.getElementById('editIsBloqueio');
    const btnClose = document.getElementById('closeModal');
    const formDelete = document.getElementById('formDeleteItem');
    
    // --- Drag and Drop ---
    let draggedBlock = null;
    let startY = 0;
    let initialTop = 0;
    
    blocks.forEach(block => {
        block.addEventListener('dragstart', (e) => {
            draggedBlock = block;
            block.classList.add('dragging');
            e.dataTransfer.setData('text/plain', block.dataset.id);
            const rect = block.getBoundingClientRect();
            startY = e.clientY - rect.top;
            initialTop = block.offsetTop;
        });
        
        block.addEventListener('dragend', (e) => {
            if (!draggedBlock) return;
            draggedBlock.classList.remove('dragging');
            
            const finalTop = block.offsetTop;
            if (finalTop !== initialTop) {
                updateBlockTimeInDB(draggedBlock);
            }
            draggedBlock = null;
        });

        // Click to edit
        block.addEventListener('click', (e) => {
            if (e.defaultPrevented) return;
            openModal(block);
        });
    });
    
    plannerGrid.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (!draggedBlock) return;
        
        const gridRect = plannerGrid.getBoundingClientRect();
        let newTop = e.clientY - gridRect.top - startY;
        
        if (newTop < 0) newTop = 0;
        const maxTop = gridRect.height - draggedBlock.offsetHeight;
        if (newTop > maxTop) newTop = maxTop;
        
        // Convert to minutes, snap to 15m, and back to percentage
        const totalMinutes = (newTop / gridRect.height) * 1440;
        const snappedMinutes = Math.round(totalMinutes / 15) * 15;
        const newPercent = (snappedMinutes / 1440) * 100;
        
        draggedBlock.style.top = newPercent + '%';
    });
    
    plannerGrid.addEventListener('drop', (e) => {
        e.preventDefault();
    });

    async function updateBlockTimeInDB(block) {
        const id = block.dataset.id;
        const gridRect = plannerGrid.getBoundingClientRect();
        
        const topPx = block.offsetTop;
        const heightPx = block.offsetHeight;
        
        const startTotalMinutes = Math.round((topPx / gridRect.height) * 1440);
        const endTotalMinutes = startTotalMinutes + Math.round((heightPx / gridRect.height) * 1440);
        
        const formatTime = (totalMins) => {
            const h = Math.floor(totalMins / 60).toString().padStart(2, '0');
            const m = (totalMins % 60).toString().padStart(2, '0');
            return `${h}:${m}`;
        };
        
        const horario_inicio = formatTime(startTotalMinutes);
        const horario_fim = formatTime(endTotalMinutes);
        
        // update UI immediately
        const timeLabel = block.querySelector('.block-time');
        if (timeLabel) timeLabel.textContent = `${horario_inicio} - ${horario_fim}`;
        
        // update dataset
        block.dataset.inicio = horario_inicio;
        block.dataset.fim = horario_fim;

        try {
            await fetch(`/update_item_rotina/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ horario_inicio, horario_fim })
            });
            // Recarregamos a página para atualizar KPIs, ou fazemos no cliente
            window.location.reload();
        } catch (e) {
            console.error("Erro ao atualizar", e);
        }
    }
    
    // --- Modal Logic ---
    function openModal(block) {
        inputId.value = block.dataset.id;
        inputNome.value = block.dataset.nome;
        inputInicio.value = block.dataset.inicio;
        inputFim.value = block.dataset.fim;
        inputIsBloqueio.checked = block.dataset.isBloqueio === 'true';
        
        formEdit.action = `/update_item_rotina/${block.dataset.id}`;
        formDelete.action = `/delete_item_rotina/${block.dataset.id}`;
        
        editModal.classList.remove('hidden');
    }
    
    btnClose.addEventListener('click', () => {
        editModal.classList.add('hidden');
    });
    
    editModal.addEventListener('click', (e) => {
        if (e.target === editModal) {
            editModal.classList.add('hidden');
        }
    });
});
