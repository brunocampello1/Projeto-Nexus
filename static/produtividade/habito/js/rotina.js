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
    
    function updateKPIs(kpis) {
        if (!kpis) return;
        const kpiCards = document.querySelectorAll('.kpi-card p');
        if (kpiCards.length >= 2) {
            kpiCards[0].textContent = kpis.horas_ocupadas + 'h';
            kpiCards[1].textContent = kpis.horas_livres + 'h';
        }
    }

    function calculateCssForBlock(horario_inicio, horario_fim) {
        const [h_ini, m_ini] = horario_inicio.split(':').map(Number);
        const [h_fim, m_fim] = horario_fim.split(':').map(Number);
        const start_min = h_ini * 60 + m_ini;
        const end_min = Math.max(start_min + 15, h_fim * 60 + m_fim);
        const css_top = (start_min / 1440.0) * 100;
        const css_height = ((end_min - start_min) / 1440.0) * 100;
        
        const dur_mins = end_min - start_min;
        const h_dur = Math.floor(dur_mins / 60);
        const m_dur = dur_mins % 60;
        let duracao_str = "";
        if (h_dur > 0 && m_dur > 0) duracao_str = `${h_dur}h ${m_dur}min`;
        else if (h_dur > 0) duracao_str = `${h_dur}h`;
        else duracao_str = `${m_dur}min`;

        return { css_top, css_height, duracao_str };
    }

    function createOrUpdateBlock(item) {
        const { css_top, css_height, duracao_str } = calculateCssForBlock(item.horario_inicio, item.horario_fim);
        const titleText = `${item.nome_display} - ${duracao_str} ${item.is_bloqueio ? 'bloqueadas' : 'dedicadas'}`;
        
        let block = document.querySelector(`.routine-block[data-id="${item.id}"]`);
        if (!block) {
            block = document.createElement('div');
            block.className = `routine-block ${item.is_bloqueio ? 'bloqueio' : ''}`;
            block.setAttribute('draggable', 'true');
            plannerGrid.appendChild(block);
            
            // Re-bind events to new block
            bindBlockEvents(block);
        } else {
            block.className = `routine-block ${item.is_bloqueio ? 'bloqueio' : ''}`;
        }

        block.title = titleText;
        block.dataset.id = item.id;
        block.dataset.nome = item.nome_display;
        block.dataset.isBloqueio = item.is_bloqueio ? 'true' : 'false';
        block.dataset.inicio = item.horario_inicio;
        block.dataset.fim = item.horario_fim;
        block.style.top = `${css_top}%`;
        block.style.height = `${css_height}%`;

        block.innerHTML = `
            <div class="block-title" title="${item.nome_display}">${item.nome_display}</div>
            <div class="block-time">${item.horario_inicio} - ${item.horario_fim}</div>
        `;
    }

    // --- Drag and Drop ---
    let draggedBlock = null;
    let startY = 0;
    let initialTop = 0;
    
    function bindBlockEvents(block) {
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

        block.addEventListener('click', (e) => {
            if (e.defaultPrevented) return;
            openModal(block);
        });
    }

    blocks.forEach(bindBlockEvents);
    
    plannerGrid.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (!draggedBlock) return;
        
        const gridRect = plannerGrid.getBoundingClientRect();
        let newTop = e.clientY - gridRect.top - startY;
        
        if (newTop < 0) newTop = 0;
        const maxTop = gridRect.height - draggedBlock.offsetHeight;
        if (newTop > maxTop) newTop = maxTop;
        
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
        
        const timeLabel = block.querySelector('.block-time');
        if (timeLabel) timeLabel.textContent = `${horario_inicio} - ${horario_fim}`;
        block.dataset.inicio = horario_inicio;
        block.dataset.fim = horario_fim;

        try {
            const response = await fetch(`/update_item_rotina/${id}`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ horario_inicio, horario_fim })
            });
            if (response.ok) {
                const data = await response.json();
                if (data.kpis) updateKPIs(data.kpis);
            }
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

    // --- Form Handlers ---
    document.addEventListener('submit', async (e) => {
        const form = e.target;
        if (!form.classList.contains('ajax-form')) return;

        const isRotina = form.classList.contains('form-add-rotina') ||
                         form.classList.contains('form-edit-rotina') ||
                         form.classList.contains('form-delete-rotina');
        
        if (!isRotina) return;
        
        e.preventDefault();

        const btn = form.querySelector('button[type="submit"]');
        let originalHtml = '';
        if (btn && form.classList.contains('form-add-rotina')) {
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
                if (data.kpis) updateKPIs(data.kpis);

                if (form.classList.contains('form-add-rotina') || form.classList.contains('form-edit-rotina')) {
                    createOrUpdateBlock(data.item);
                    if (form.classList.contains('form-add-rotina')) {
                        // reset partially
                        form.querySelector('input[name="habito_nome"]').value = '';
                    }
                    if (form.classList.contains('form-edit-rotina')) editModal.classList.add('hidden');
                }
                else if (form.classList.contains('form-delete-rotina')) {
                    const block = document.querySelector(`.routine-block[data-id="${data.id}"]`);
                    if (block) block.remove();
                    editModal.classList.add('hidden');
                }
            }
        } catch (error) {
            console.error(error);
        } finally {
            if (btn && document.body.contains(btn) && form.classList.contains('form-add-rotina')) {
                btn.innerHTML = originalHtml;
                btn.disabled = false;
            }
        }
    });
});
