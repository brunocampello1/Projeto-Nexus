// Novo: Gerenciar alteração de status via dropdown nativo
async function changeStatus(tarefaId, novoStatus) {
    try {
        const response = await fetch(`/update_tarefa_status/${tarefaId}/${novoStatus}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Falha ao atualizar status');
        }

        const result = await response.json();

        // Atualizar a classe do select para ajustar cor
        const select = document.getElementById('status-select-' + tarefaId);
        if (select) {
            select.className = 'status-select status-' + result.status;
        }

    } catch (err) {
        console.error(err);
    }
}

// Mantém compatibilidade: nada a fechar no clique externo necessário, select fecha sozinho
