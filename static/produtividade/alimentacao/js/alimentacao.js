(function() {
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDarkMode ? '#F8FAFC' : '#0F172A';
    const gridColor = isDarkMode ? '#1E293B' : '#E2E8F0';
    
    let chartPesoInstance = null;
    let chartCaloriasInstance = null;

    function initCharts() {
        // Destroy any existing Chart.js instances (important for SPA re-navigation)
        if (typeof Chart !== 'undefined') {
            const existingCharts = Object.values(Chart.instances || {});
            existingCharts.forEach(chart => {
                try { chart.destroy(); } catch(e) {}
            });
        }
        const ctxPeso = document.getElementById('chartPeso');
        if (ctxPeso && typeof window.graficoPesoData !== 'undefined') {
            const labelsPeso = window.graficoPesoData.map(d => d.x);
            const dataPeso = window.graficoPesoData.map(d => d.y);

            chartPesoInstance = new Chart(ctxPeso, {
                type: 'line',
                data: {
                    labels: labelsPeso,
                    datasets: [{
                        label: 'Peso (kg)',
                        data: dataPeso,
                        borderColor: '#D4AF37',
                        backgroundColor: 'rgba(212, 175, 55, 0.15)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
                        pointBackgroundColor: '#D4AF37'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: textColor }, grid: { color: gridColor } },
                        y: { ticks: { color: textColor }, grid: { color: gridColor } }
                    }
                }
            });
        }

        const ctxCal = document.getElementById('chartCalorias');
        if (ctxCal && typeof window.graficoCaloriasData !== 'undefined') {
            const labelsCal = window.graficoCaloriasData.map(d => d.x);
            const dataDieta = window.graficoCaloriasData.map(d => d.dieta);
            const dataExtra = window.graficoCaloriasData.map(d => d.extra);

            const customDataLabelsPlugin = {
                id: 'customDataLabels',
                afterDatasetsDraw(chart, args, options) {
                    const {ctx} = chart;
                    ctx.save();
                    ctx.font = 'bold 11px "Plus Jakarta Sans", sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    
                    const totals = new Array(chart.data.labels.length).fill(0);
                    const topY = new Array(chart.data.labels.length).fill(null);
                    
                    chart.data.datasets.forEach((dataset, datasetIndex) => {
                        const meta = chart.getDatasetMeta(datasetIndex);
                        if(meta.hidden) return;
                        
                        meta.data.forEach((element, index) => {
                            const val = dataset.data[index];
                            totals[index] += val;
                            
                            if (val > 0) {
                                if (topY[index] === null || element.y < topY[index]) {
                                    topY[index] = element.y;
                                }
                                ctx.fillStyle = '#FFFFFF';
                                const yCenter = (element.y + element.base) / 2;
                                ctx.fillText(val, element.x, yCenter);
                            }
                        });
                    });
                    
                    ctx.fillStyle = textColor;
                    ctx.textBaseline = 'bottom';
                    totals.forEach((total, index) => {
                        if (total > 0 && topY[index] !== null) {
                            const meta = chart.getDatasetMeta(0);
                            const element = meta.data[index];
                            ctx.fillText(total, element.x, topY[index] - 4);
                        }
                    });
                    
                    ctx.restore();
                }
            };

            chartCaloriasInstance = new Chart(ctxCal, {
                type: 'bar',
                data: {
                    labels: labelsCal,
                    datasets: [
                        { label: 'Refeição Planejada', data: dataDieta, backgroundColor: '#F8FAFC', borderRadius: 4 },
                        { label: 'Vilões (Extra)', data: dataExtra, backgroundColor: '#D946EF', borderRadius: 4 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true, position: 'top', labels: { color: textColor, font: { size: 10 } } } },
                    scales: {
                        x: { stacked: true, ticks: { color: textColor }, grid: { display: false } },
                        y: { stacked: true, ticks: { color: textColor }, grid: { color: gridColor }, grace: '10%' }
                    }
                },
                plugins: [customDataLabelsPlugin]
            });
        }
    }

    initCharts();

    // DOM Updates
    function updateKPIs(kpis) {
        if (!kpis) return;
        const kpisContainer = document.querySelector('.kpis-container');
        if (kpisContainer) {
            const dangerClass = (kpis.meta - kpis.diario < 0) ? 'danger' : '';
            const statusText = (kpis.meta - kpis.diario >= 0) ? 'restantes' : 'estouradas';
            const delta = kpis.peso_atual - kpis.peso_anterior;
            const sign = delta > 0 ? '+' : '';
            const pesoText = kpis.peso_anterior > 0 ? `${sign}${delta.toFixed(2)} kg desde o último registro` : 'Primeiro registro';
            
            kpisContainer.innerHTML = `
                <div class="kpi-card">
                    <h3>Consumo Hoje</h3>
                    <p class="${dangerClass}">${kpis.diario} / ${kpis.meta} kcal</p>
                    <small>${Math.abs(kpis.meta - kpis.diario)} kcal ${statusText}</small>
                </div>
                <div class="kpi-card">
                    <h3>Tendência de Peso</h3>
                    <p>${kpis.peso_atual} kg</p>
                    <small>${pesoText}</small>
                </div>
                <div class="kpi-card">
                    <h3>Acumulado (7 dias)</h3>
                    <p>${kpis.semanal} kcal</p>
                </div>
                <div class="kpi-card">
                    <h3>Acumulado Mensal</h3>
                    <p>${kpis.mensal} kcal</p>
                </div>
            `;
        }
    }

    function updateCharts(pesoData, caloriasData) {
        if (chartPesoInstance && pesoData) {
            chartPesoInstance.data.labels = pesoData.map(d => d.x);
            chartPesoInstance.data.datasets[0].data = pesoData.map(d => d.y);
            chartPesoInstance.update();
        }
        if (chartCaloriasInstance && caloriasData) {
            chartCaloriasInstance.data.labels = caloriasData.map(d => d.x);
            chartCaloriasInstance.data.datasets[0].data = caloriasData.map(d => d.dieta);
            chartCaloriasInstance.data.datasets[1].data = caloriasData.map(d => d.extra);
            chartCaloriasInstance.update();
        }
    }

    function addRegistroToTable(registro, dataStr) {
        const tableWrap = document.querySelector('.table-wrap');
        const emptyState = document.querySelector('.empty-state');
        
        let tbody;
        if (emptyState) {
            emptyState.remove();
            const historyCard = document.querySelector('.card-history');
            const newTableWrap = document.createElement('div');
            newTableWrap.className = 'table-wrap';
            newTableWrap.innerHTML = `
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Alimento / Refeição</th>
                            <th>Calorias</th>
                            <th>Tipo</th>
                            <th>Ação</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            `;
            historyCard.appendChild(newTableWrap);
            tbody = newTableWrap.querySelector('tbody');
        } else if (tableWrap) {
            tbody = tableWrap.querySelector('tbody');
        }

        if (tbody) {
            const tr = document.createElement('tr');
            tr.setAttribute('data-id', registro.id);
            tr.innerHTML = `
                <td>${registro.nome}</td>
                <td>${registro.calorias} kcal</td>
                <td><span class="badge ${registro.tipo.toLowerCase()}">${registro.tipo}</span></td>
                <td>
                    <form action="/delete_registro_alimentacao/${registro.id}" method="POST" style="margin:0;" class="ajax-form form-delete-registro">
                        <input type="hidden" name="data" value="${dataStr}">
                        <button type="submit" class="btn-icon btn-danger" title="Excluir"><i class="ph ph-trash"></i></button>
                    </form>
                </td>
            `;
            tbody.appendChild(tr);
        }
    }

    function removeRegistroFromTable(registroId) {
        const tr = document.querySelector(`tr[data-id="${registroId}"]`);
        if (tr) tr.remove();
        
        const tbody = document.querySelector('.history-table tbody');
        if (tbody && tbody.children.length === 0) {
            const tableWrap = document.querySelector('.table-wrap');
            if (tableWrap) {
                tableWrap.insertAdjacentHTML('afterend', '<p class="empty-state">Nenhum registro para este dia.</p>');
                tableWrap.remove();
            }
        }
    }

    // Listener global para os formulários de Alimentação
    document.addEventListener('submit', async (e) => {
        const form = e.target;
        if (!form.classList.contains('ajax-form')) return;
        
        // Verifica se é de alimentação verificando as classes
        const isAlimentacao = form.classList.contains('form-add-dieta') || 
                              form.classList.contains('form-remove-dieta') ||
                              form.classList.contains('form-add-refeicao') ||
                              form.classList.contains('form-delete-refeicao') ||
                              form.classList.contains('form-add-vilao') ||
                              form.classList.contains('form-delete-registro') ||
                              form.classList.contains('form-update-metas');
                              
        if (!isAlimentacao) return;

        if (form.dataset.submitting) {
            e.preventDefault();
            return;
        }

        e.preventDefault();
        form.dataset.submitting = 'true';

        const btn = e.submitter || form.querySelector('button[type="submit"]');
        let originalHtml = '';
        if (btn && !btn.hasAttribute('data-original-html')) {
            originalHtml = btn.innerHTML;
            btn.setAttribute('data-original-html', originalHtml);
            btn.innerHTML = '<i class="ph ph-spinner ph-spin"></i>';
            btn.disabled = true;
        } else if (btn) {
            originalHtml = btn.getAttribute('data-original-html');
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
                if (data.grafico_peso || data.grafico_calorias) updateCharts(data.grafico_peso, data.grafico_calorias);

                // Manipulações específicas
                const dataStr = form.querySelector('input[name="data"]')?.value;

                if (form.classList.contains('form-add-dieta')) {
                    // Muda para checked
                    form.classList.remove('form-add-dieta');
                    form.classList.add('form-remove-dieta');
                    form.action = '/remove_registro_dieta';
                    form.innerHTML = `
                        <input type="hidden" name="data" value="${dataStr}">
                        <input type="hidden" name="nome" value="${data.registro.nome}">
                        <button type="submit" class="btn-check checked"><i class="ph ph-check-square"></i></button>
                    `;
                    addRegistroToTable(data.registro, dataStr);
                } 
                else if (form.classList.contains('form-remove-dieta')) {
                    // Muda para unchecked
                    form.classList.remove('form-remove-dieta');
                    form.classList.add('form-add-dieta');
                    form.action = '/add_registro_alimentacao';
                    const calText = form.parentElement.querySelector('.refeicao-nome').textContent;
                    const calMatch = calText.match(/\((\d+)\s*kcal\)/);
                    const cal = calMatch ? calMatch[1] : 0;
                    
                    form.innerHTML = `
                        <input type="hidden" name="data" value="${dataStr}">
                        <input type="hidden" name="nome" value="${data.nome}">
                        <input type="hidden" name="calorias" value="${cal}">
                        <input type="hidden" name="tipo" value="Dieta">
                        <button type="submit" class="btn-check"><i class="ph ph-square"></i></button>
                    `;
                    const trs = document.querySelectorAll('.history-table tbody tr');
                    trs.forEach(tr => {
                        if (tr.children[0].textContent === data.nome) tr.remove();
                    });
                    const tbody = document.querySelector('.history-table tbody');
                    if (tbody && tbody.children.length === 0) {
                        const tableWrap = document.querySelector('.table-wrap');
                        if (tableWrap) {
                            tableWrap.insertAdjacentHTML('afterend', '<p class="empty-state">Nenhum registro para este dia.</p>');
                            tableWrap.remove();
                        }
                    }
                }
                else if (form.classList.contains('form-add-vilao')) {
                    addRegistroToTable(data.registro, dataStr);
                    form.reset();
                }
                else if (form.classList.contains('form-delete-registro')) {
                    removeRegistroFromTable(data.id);
                }
                else if (form.classList.contains('form-add-refeicao')) {
                    const newDiv = document.createElement('div');
                    newDiv.className = 'refeicao-item';
                    newDiv.style = "display:flex; align-items:center;";
                    newDiv.innerHTML = `
                        <form action="/add_registro_alimentacao" method="POST" style="margin:0;" class="ajax-form form-add-dieta">
                            <input type="hidden" name="data" value="${dataStr || new Date().toISOString().split('T')[0]}">
                            <input type="hidden" name="nome" value="${data.refeicao.nome}">
                            <input type="hidden" name="calorias" value="${data.refeicao.calorias}">
                            <input type="hidden" name="tipo" value="Dieta">
                            <button type="submit" class="btn-check"><i class="ph ph-square"></i></button>
                        </form>
                        <span class="refeicao-nome">${data.refeicao.nome} (${data.refeicao.calorias} kcal)</span>
                        <form action="/delete_refeicao_fixa/${data.refeicao.id}" method="POST" style="margin: 0 0 0 auto;" onsubmit="return confirm('Deseja remover esta refeição do seu cardápio fixo?');" class="ajax-form form-delete-refeicao">
                            <button type="submit" class="btn-icon btn-danger" title="Excluir Refeição Fixa" style="padding: 2px;"><i class="ph ph-trash"></i></button>
                        </form>
                    `;
                    const hr = document.querySelector('.card-checklist hr');
                    if (hr) hr.parentNode.insertBefore(newDiv, hr);
                    form.reset();
                }
                else if (form.classList.contains('form-delete-refeicao')) {
                    form.closest('.refeicao-item').remove();
                }
            }
        } catch (error) {
            console.error(error);
        } finally {
            delete form.dataset.submitting;
            if (btn && document.body.contains(btn)) {
                btn.innerHTML = originalHtml || btn.getAttribute('data-original-html') || btn.innerHTML;
                btn.removeAttribute('data-original-html');
                btn.disabled = false;
            }
        }
    });
})();
