document.addEventListener('DOMContentLoaded', () => {
    
    // --- Update Progress Helper ---
    function updateProgress(tarefaId, progresso) {
        const taskCard = document.querySelector(`.task-card[data-id="${tarefaId}"]`);
        if (!taskCard) return;
        const progressBar = taskCard.querySelector('.progress-bar');
        const progressText = taskCard.querySelector('.progress-text');
        if (progressBar) progressBar.style.width = `${progresso}%`;
        if (progressText) progressText.textContent = `${progresso}% Concluído`;
    }

    // --- Form Handlers ---
    document.addEventListener('submit', async (e) => {
        const form = e.target;
        if (!form.classList.contains('ajax-form')) return;

        const isTarefa = form.classList.contains('form-add-tarefa') ||
                         form.classList.contains('form-delete-tarefa') ||
                         form.classList.contains('form-add-subtarefa') ||
                         form.classList.contains('form-delete-subtarefa');
        
        if (!isTarefa) return;
        
        if (form.dataset.submitting) {
            e.preventDefault();
            return;
        }

        e.preventDefault();
        form.dataset.submitting = 'true';

        const btn = e.submitter || form.querySelector('button[type="submit"]');
        let originalHtml = '';
        if (btn && form.classList.contains('form-add-tarefa')) {
            if (!btn.hasAttribute('data-original-html')) {
                originalHtml = btn.innerHTML;
                btn.setAttribute('data-original-html', originalHtml);
                btn.innerHTML = '...';
                btn.disabled = true;
            } else {
                originalHtml = btn.getAttribute('data-original-html');
            }
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
                
                if (form.classList.contains('form-add-tarefa')) {
                    const taskList = document.getElementById('tasks-list');
                    // Remove "Nenhuma tarefa cadastrada" if exists
                    const emptyState = taskList.querySelector('p');
                    if (emptyState && !emptyState.classList.contains('task-card')) emptyState.remove();

                    const t = data.tarefa;
                    const div = document.createElement('div');
                    div.className = 'card task-card';
                    div.setAttribute('draggable', 'true');
                    div.dataset.id = t.id;
                    div.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; gap: 1rem;">
                            <div onclick="toggleSubtasks(${t.id})" style="flex: 1; display: flex; align-items: center; cursor: pointer; user-select: none; gap: 0.5rem;">
                                <h3 style="margin: 0; font-size: 1rem;">${t.titulo}</h3>
                                <i class="ph ph-caret-down" id="arrow-${t.id}" style="font-size: 1.2rem; color: var(--text-secondary); transition: transform 0.3s ease; flex-shrink: 0; transform: rotate(-90deg);"></i>
                            </div>
                            
                            <div class="status-wrapper">
                                <select id="status-select-${t.id}" class="status-select status-${t.status}" onchange="changeStatus(${t.id}, this.value)">
                                    <option value="em-andamento" ${t.status === 'em-andamento' ? 'selected' : ''}>Em andamento</option>
                                    <option value="refinamento" ${t.status === 'refinamento' ? 'selected' : ''}>Refinamento</option>
                                    <option value="concluida" ${t.status === 'concluida' ? 'selected' : ''}>Concluída</option>
                                    <option value="pendente-base" ${t.status === 'pendente-base' ? 'selected' : ''}>Pendente Base</option>
                                </select>
                            </div>
                            
                            <form action="/delete_tarefa/${t.id}" method="POST" style="margin: 0;" onsubmit="return confirm('Tem certeza que deseja excluir esta tarefa e TODAS as suas subtarefas?');" class="ajax-form form-delete-tarefa">
                                <button type="submit" class="delete-btn" title="Excluir Tarefa"><i class="ph ph-trash"></i></button>
                            </form>
                        </div>
                        
                        <div>
                            <div class="progress-bar-container">
                                <div class="progress-bar" style="width: ${t.progresso}%;"></div>
                            </div>
                            <p class="progress-text">${t.progresso}% Concluído</p>
                        </div>
                        
                        <div id="subtasks-${t.id}" style="margin-top: 0.75rem; display: none;">
                            <ul class="subtask-list"></ul>
                            <form action="/add_subtarefa/${t.id}" method="POST" class="add-subtask-form ajax-form form-add-subtarefa">
                                <input type="text" name="descricao" placeholder="Adicionar subtarefa..." required style="flex: 1;">
                                <button type="submit"><i class="ph ph-plus"></i></button>
                            </form>
                        </div>
                    `;
                    taskList.appendChild(div);
                    form.reset();
                }
                else if (form.classList.contains('form-delete-tarefa')) {
                    const taskCard = document.querySelector(`.task-card[data-id="${data.id}"]`);
                    if (taskCard) taskCard.remove();
                    
                    const taskList = document.getElementById('tasks-list');
                    if (taskList.children.length === 0) {
                        taskList.innerHTML = `<p style="color: var(--text-secondary);">Nenhuma tarefa cadastrada. Crie uma acima!</p>`;
                    }
                }
                else if (form.classList.contains('form-add-subtarefa')) {
                    const sub = data.subtarefa;
                    const subtaskList = document.querySelector(`#subtasks-${sub.tarefa_id} .subtask-list`);
                    if (subtaskList) {
                        const li = document.createElement('li');
                        li.className = 'subtask-item';
                        li.innerHTML = `
                            <div style="display: flex; align-items: center; gap: 0.5rem; flex: 1;">
                                <button type="button" class="toggle-btn subtask-toggle-btn"
                                        data-subtarefa="${sub.id}"
                                        style="background: none; border: none;">
                                    <i class="ph ph-circle"></i>
                                </button>
                                <span>${sub.descricao}</span>
                            </div>
                            <form action="/delete_subtarefa/${sub.id}" method="POST" style="margin: 0;" onsubmit="return confirm('Excluir subtarefa?');" class="ajax-form form-delete-subtarefa">
                                <button type="submit" class="delete-btn" title="Excluir Subtarefa"><i class="ph ph-trash"></i></button>
                            </form>
                        `;
                        subtaskList.appendChild(li);
                    }
                    updateProgress(sub.tarefa_id, data.progresso);
                    form.reset();
                }
                else if (form.classList.contains('form-delete-subtarefa')) {
                    const li = form.closest('.subtask-item');
                    if (li) li.remove();
                    updateProgress(data.tarefa_id, data.progresso);
                }
            }
        } catch (error) {
            console.error(error);
        } finally {
            delete form.dataset.submitting;
            if (btn && document.body.contains(btn) && form.classList.contains('form-add-tarefa')) {
                btn.innerHTML = originalHtml || btn.getAttribute('data-original-html') || btn.innerHTML;
                btn.removeAttribute('data-original-html');
                btn.disabled = false;
            }
        }
    });
});
