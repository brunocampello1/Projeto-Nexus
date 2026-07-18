document.addEventListener('DOMContentLoaded', () => {
    applySavedTheme();

    document.querySelectorAll('.habit-toggle').forEach(button => {
        button.addEventListener('click', handleHabitToggle);
    });

    document.querySelectorAll('.meta-input').forEach(input => {
        input.addEventListener('change', handleMetaChange);
    });

    document.querySelectorAll('.subtask-toggle-btn').forEach(button => {
        button.addEventListener('click', handleSubtaskToggle);
    });

    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            applyTheme(current === 'dark' ? 'light' : 'dark');
        });
    }

    // Controle de Sidebar Responsiva (Mobile)
    const sidebar = document.getElementById('sidebar');
    const hamburgerBtn = document.getElementById('hamburgerBtn');
    const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    function toggleSidebar() {
        sidebar.classList.toggle('show');
        sidebarOverlay.classList.toggle('show');
        document.body.classList.toggle('no-scroll');
    }

    if (hamburgerBtn && sidebar && sidebarOverlay) {
        hamburgerBtn.addEventListener('click', toggleSidebar);
    }
    if (sidebarCloseBtn) {
        sidebarCloseBtn.addEventListener('click', toggleSidebar);
    }
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', toggleSidebar);

// Produtividade submenu toggle
const productivityToggle = document.getElementById('productivityToggle');
const productivitySubmenu = document.getElementById('productivitySubmenu');
if (productivityToggle && productivitySubmenu) {
  productivityToggle.addEventListener('click', () => {
    const expanded = productivityToggle.getAttribute('aria-expanded') === 'true';
    productivityToggle.setAttribute('aria-expanded', !expanded);
    productivitySubmenu.style.display = expanded ? 'none' : 'block';
    const arrow = productivityToggle.querySelector('.submenu-arrow');
    if (arrow) {
      arrow.style.transform = expanded ? 'rotate(0deg)' : 'rotate(180deg)';
    }
  });
}

    }

    // Navegação Semanal por AJAX (SPA-style) para evitar page reloads e agilizar cliques
    document.body.addEventListener('click', async (event) => {
        const navBtn = event.target.closest('.nav-week-btn-small');
        if (!navBtn) return;
        
        event.preventDefault();
        const url = navBtn.getAttribute('href');
        if (!url) return;
        
        try {
            const tableContainer = document.querySelector('.habits-table-container');
            if (tableContainer) tableContainer.style.opacity = '0.6';

            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            if (!response.ok) throw new Error('Falha ao carregar semana');
            
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Atualizar URL sem recarregar a página
            window.history.pushState({}, '', url);
            
            // 1. Atualizar Tabela
            const newTable = doc.querySelector('.habits-table-container');
            const currentTable = document.querySelector('.habits-table-container');
            if (newTable && currentTable) {
                currentTable.innerHTML = newTable.innerHTML;
            }
            
            // 2. Atualizar KPIs
            const newKpis = doc.querySelector('.kpis-container');
            const currentKpis = document.querySelector('.kpis-container');
            if (newKpis && currentKpis) {
                currentKpis.innerHTML = newKpis.innerHTML;
            }
            
            // 3. Atualizar Ranking
            const newRanking = doc.querySelector('.ranking-card');
            const currentRanking = document.querySelector('.ranking-card');
            if (newRanking && currentRanking) {
                currentRanking.innerHTML = newRanking.innerHTML;
            }
            
            // Re-associar listeners de eventos
            document.querySelectorAll('.habit-toggle').forEach(button => {
                button.addEventListener('click', handleHabitToggle);
            });
            document.querySelectorAll('.meta-input').forEach(input => {
                input.addEventListener('change', handleMetaChange);
            });
            
            if (tableContainer) tableContainer.style.opacity = '1';
        } catch (error) {
            console.error(error);
            window.location.href = url;
        }
    });
});

function applySavedTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);

    const toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    if (theme === 'dark') {
        toggle.innerHTML = '<i class="ph ph-sun"></i><span>Modo claro</span>';
    } else {
        toggle.innerHTML = '<i class="ph ph-moon"></i><span>Modo escuro</span>';
    }
}

async function handleHabitToggle(event) {
    const button = event.currentTarget;
    const habitoId = button.dataset.habito;
    const data = button.dataset.data;

    if (!habitoId || !data) {
        return;
    }

    // Pegar o week_offset da URL corrente
    const urlParams = new URLSearchParams(window.location.search);
    const weekOffset = urlParams.get('week_offset') || '0';

    button.disabled = true;
    try {
        const response = await fetch(`/toggle_habito/${habitoId}/${data}?week_offset=${weekOffset}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error('Falha ao atualizar hábito');
        }

        const result = await response.json();
        const icon = button.querySelector('i');

        if (result.concluido) {
            button.classList.add('active');
            if (icon) icon.className = 'ph-fill ph-check-circle';
        } else {
            button.classList.remove('active');
            if (icon) icon.className = 'ph ph-circle';
        }

        // Atualizar KPIs em tempo real
        if (result.kpis && result.tendencia) {
            updateKPIsOnPage(result.kpis, result.tendencia);
        }
    } catch (error) {
        console.error(error);
    } finally {
        button.disabled = false;
    }
}

function updateKPIsOnPage(kpis, tendencia) {
    // Atualizar Taxa de Conclusão Geral
    const taxaElement = document.querySelector('.kpi-main .kpi-value');
    if (taxaElement) {
        taxaElement.textContent = kpis.taxa_conclusao_geral + '%';
    }

    // Atualizar Tendência
    const trendCard = document.querySelector('.kpi-trend');
    const trendValue = document.querySelector('.kpi-trend .kpi-value');
    const trendIcon = document.querySelector('.kpi-trend .kpi-header i');
    
    if (trendCard && trendValue && trendIcon) {
        // Remover classes de direção anterior
        trendCard.classList.remove('trend-up', 'trend-down', 'trend-stable');
        
        // Adicionar nova classe de direção
        trendCard.classList.add(`trend-${tendencia.direcao}`);
        
        // Atualizar valor
        const sinal = tendencia.direcao === 'up' ? '+' : (tendencia.direcao === 'down' ? '-' : '');
        trendValue.textContent = sinal + tendencia.diferenca + '%';
        
        // Atualizar ícone
        if (tendencia.direcao === 'up') {
            trendIcon.className = 'ph ph-trend-up';
        } else if (tendencia.direcao === 'down') {
            trendIcon.className = 'ph ph-trend-down';
        } else {
            trendIcon.className = 'ph ph-minus';
        }
    }

    // Atualizar Melhor Hábito
    const bestValue = document.querySelector('.kpi-best .kpi-value');
    const bestDesc = document.querySelector('.kpi-best .kpi-description');
    
    if (bestValue && bestDesc && kpis.melhor_habito) {
        bestValue.textContent = kpis.melhor_habito.taxa + '%';
        bestDesc.textContent = kpis.melhor_habito.nome;
    }

    // Atualizar Maior Sequência
    const maxStreak = Math.max(...Object.values(kpis.streaks), 0);
    const streakValue = document.querySelector('.kpi-streak .kpi-value');
    if (streakValue) {
        streakValue.textContent = maxStreak;
    }

    // Atualizar Ranking de Performance
    updateRankingTable(kpis.habitos_por_performance);
}

async function handleMetaChange(event) {
    const input = event.currentTarget;
    const habitoId = input.dataset.habito;
    const metaDias = parseInt(input.value, 10);

    if (!habitoId || isNaN(metaDias) || metaDias < 0 || metaDias > 7) return;

    // Pegar o week_offset da URL corrente
    const urlParams = new URLSearchParams(window.location.search);
    const weekOffset = urlParams.get('week_offset') || '0';

    try {
        const response = await fetch(`/update_meta_habito/${habitoId}/${metaDias}?week_offset=${weekOffset}`, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        if (!response.ok) throw new Error('Falha ao atualizar meta');

        const result = await response.json();
        if (result.kpis && result.tendencia) {
            updateKPIsOnPage(result.kpis, result.tendencia);
        }
    } catch (error) {
        console.error(error);
    }
}

function updateRankingTable(habitosPorPerformance) {
    const rankingList = document.querySelector('.ranking-list');
    if (!rankingList) return;

    // Limpar ranking anterior
    rankingList.innerHTML = '';

    // Recriar itens do ranking
    habitosPorPerformance.forEach((habito, index) => {
        const item = document.createElement('div');
        item.className = 'ranking-item' + (habito.meta_atingida ? ' meta-atingida' : '');
        
        const posicao = document.createElement('div');
        posicao.className = 'ranking-position';
        posicao.textContent = index + 1;
        
        const info = document.createElement('div');
        info.className = 'ranking-info';
        
        const nome = document.createElement('div');
        nome.className = 'ranking-name';
        nome.textContent = habito.nome;
        
        const stats = document.createElement('div');
        stats.className = 'ranking-stats';
        
        let checkCircleHtml = '';
        if (habito.meta_atingida) {
            checkCircleHtml = `<i class="ph-fill ph-check-circle" style="color: #10B981; margin-left: 0.5rem;"></i>`;
        }
        
        stats.innerHTML = `
            <span class="conclusoes-meta" title="dias concluídos / total dias no período">${habito.conclusoes}/${habito.total_periodo}d</span>
            ${checkCircleHtml}
            <span class="ranking-streak-divider" style="margin: 0 0.25rem; opacity: 0.4;">|</span>
            <i class="ph ph-fire" style="color: #ff6b35; margin-right: 0.25rem;"></i>
            <span class="streak-value" style="font-weight: 500;">${habito.streak} dias</span>
            <span class="ranking-streak-divider" style="margin: 0 0.25rem; opacity: 0.4;">|</span>
            <span style="color: var(--text-secondary); font-size: 0.75rem;">desde ${habito.data_criacao || ''}</span>
            <button class="honeycomb-btn" data-habito-id="${habito.id}" data-habito-nome="${habito.nome}" title="Ver histórico de colmeia" type="button">
                <i class="ph-fill ph-hexagon"></i>
            </button>
        `;
        
        info.appendChild(nome);
        info.appendChild(stats);
        
        const progress = document.createElement('div');
        progress.className = 'ranking-progress';
        
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';
        
        const progressFill = document.createElement('div');
        progressFill.className = 'progress-fill';
        progressFill.style.width = habito.taxa + '%';
        
        const progressText = document.createElement('span');
        progressText.className = 'progress-text';
        progressText.textContent = habito.taxa + '%';
        
        progressBar.appendChild(progressFill);
        progress.appendChild(progressBar);
        progress.appendChild(progressText);
        
        item.appendChild(posicao);
        item.appendChild(info);
        item.appendChild(progress);
        
        rankingList.appendChild(item);
    });
}

async function handleSubtaskToggle(event) {
    const button = event.currentTarget;
    const subtarefaId = button.dataset.subtarefa;

    if (!subtarefaId) {
        return;
    }

    button.disabled = true;
    try {
        const response = await fetch(`/toggle_subtarefa/${subtarefaId}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error('Falha ao atualizar subtarefa');
        }

        const result = await response.json();
        const icon = button.querySelector('i');
        const item = button.closest('.subtask-item');
        const card = button.closest('.card');
        const progressBar = card?.querySelector('.progress-bar');
        const progressText = card?.querySelector('.progress-text');

        if (result.concluida) {
            button.classList.add('active');
            if (icon) icon.className = 'ph-fill ph-check-circle';
            if (item) item.querySelector('span')?.classList.add('strikethrough');
        } else {
            button.classList.remove('active');
            if (icon) icon.className = 'ph ph-circle';
            if (item) item.querySelector('span')?.classList.remove('strikethrough');
        }

        if (progressBar) {
            progressBar.style.width = `${result.progresso}%`;
        }
        if (progressText) {
            progressText.textContent = `${result.progresso}% Concluído`;
        }
    } catch (error) {
        console.error(error);
    } finally {
        button.disabled = false;
    }
}

// ==========================================
// CONTROLE DO GRÁFICO DE COLMEIA (MODAL)
// ==========================================

// Listener delegado para cliques nos botões de colmeia
document.addEventListener('click', (event) => {
    const btn = event.target.closest('.honeycomb-btn');
    if (btn) {
        const habitoId = btn.dataset.habitoId;
        const habitoNome = btn.dataset.habitoNome;
        if (habitoId && habitoNome) {
            showHoneycombModal(habitoId, habitoNome);
        }
    }
});

// Listener global para fechar clicando fora do modal
window.addEventListener('click', (event) => {
    const modal = document.getElementById('honeycombModal');
    if (event.target === modal) {
        closeHoneycombModal();
    }
});

// Fechar com a tecla ESC
window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeHoneycombModal();
    }
});

async function showHoneycombModal(habitoId, habitoNome) {
    const modal = document.getElementById('honeycombModal');
    const modalTitle = document.getElementById('modalHabitName');
    const loading = document.getElementById('honeycombLoading');
    const content = document.getElementById('honeycombContent');
    
    if (!modal) return;
    
    // Set habit name in header
    if (modalTitle) modalTitle.textContent = `Histórico: ${habitoNome}`;
    
    // Show modal and loading spinner
    modal.style.display = 'flex';
    // Trigger CSS opacity transition after display flex
    setTimeout(() => modal.classList.add('show'), 10);
    
    if (loading) loading.style.display = 'flex';
    if (content) content.style.display = 'none';
    
    try {
        const response = await fetch(`/habito/${habitoId}/history`);
        if (!response.ok) {
            throw new Error('Falha ao buscar dados de histórico');
        }
        
        const data = await response.json();
        
        // Render colmeia SVG
        drawHoneycomb(data.history);
        
        // Update stats
        const completionsEl = document.getElementById('hcStatCompletions');
        const rateEl = document.getElementById('hcStatRate');
        const streakEl = document.getElementById('hcStatStreak');
        
        if (completionsEl) completionsEl.textContent = `${data.total_concluidos} / 30`;
        if (rateEl) rateEl.textContent = `${data.taxa_sucesso}%`;
        if (streakEl) streakEl.textContent = `${data.streak} dias`;
        
        // Show content
        if (loading) loading.style.display = 'none';
        if (content) content.style.display = 'block';
        
    } catch (error) {
        console.error(error);
        if (loading) {
            loading.innerHTML = `
                <i class="ph ph-warning-circle" style="font-size: 2rem; color: var(--danger-color);"></i>
                <p>Erro ao carregar o histórico de colmeia.</p>
            `;
        }
    }
}

function closeHoneycombModal() {
    const modal = document.getElementById('honeycombModal');
    if (!modal) return;
    
    modal.classList.remove('show');
    // Hide after transition ends (250ms)
    setTimeout(() => {
        modal.style.display = 'none';
    }, 250);
    
    // Hide tooltip
    const tooltip = document.getElementById('honeycombTooltip');
    if (tooltip) tooltip.classList.remove('show');
}

function drawHoneycomb(history) {
    const container = document.getElementById('honeycombChartContainer');
    if (!container) return;
    
    const R = 22; // Raio do hexágono (distância do centro ao vértice / tamanho do lado)
    const H = Math.sqrt(3) * R; // Altura do hexágono
    const dx = 1.5 * R; // Passo horizontal entre colunas
    const dy = H; // Passo vertical entre linhas
    const padX = 25; // Margem interna esquerda
    const padY = 25; // Margem interna superior
    
    let svgHtml = `<svg viewBox="0 0 240 240" width="100%" height="100%">`;
    
    history.forEach((day, index) => {
        // Layout: 6 colunas, 5 linhas = 30 dias
        const c = index % 6;
        const r = Math.floor(index / 6);
        
        // Coordenadas do centro da célula hexagon
        const cx = padX + c * dx;
        // Shift de meia altura na linha se for coluna ímpar (ondulação da colmeia)
        const cy = padY + r * dy + (c % 2 === 1 ? dy / 2 : 0);
        
        // Escala o raio de desenho ligeiramente para baixo para criar espaçamento (gap) uniforme
        const R_draw = R * 0.88;
        const points = [];
        for (let j = 0; j < 6; j++) {
            const angle = (j * 60) * Math.PI / 180;
            const x = cx + R_draw * Math.cos(angle);
            const y = cy + R_draw * Math.sin(angle);
            points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
        }
        
        const colorClass = day.concluido ? 'var(--success-color)' : 'rgba(148, 163, 184, 0.15)';
        const strokeColor = day.concluido ? 'rgba(16, 185, 129, 0.4)' : 'var(--border-color)';
        const statusText = day.concluido ? 'Concluído' : 'Não concluído';
        
        const parts = day.data.split('-');
        const dateFormatted = `${parts[2]}/${parts[1]}/${parts[0]}`;
        
        svgHtml += `
            <polygon 
                points="${points.join(' ')}" 
                fill="${colorClass}" 
                stroke="${strokeColor}" 
                stroke-width="1.5"
                class="hexagon-cell"
                data-date="${dateFormatted}"
                data-status="${statusText}"
                data-concluido="${day.concluido}"
            />
        `;
    });
    
    svgHtml += `</svg>`;
    container.innerHTML = svgHtml;
    
    setupHoneycombTooltipListeners();
}

function setupHoneycombTooltipListeners() {
    const tooltip = document.getElementById('honeycombTooltip');
    const container = document.getElementById('honeycombChartContainer');
    
    if (!tooltip || !container) return;
    
    // Remover listeners anteriores para evitar duplicações
    container.replaceWith(container.cloneNode(true));
    const newContainer = document.getElementById('honeycombChartContainer');
    
    newContainer.addEventListener('mouseover', (event) => {
        const hex = event.target.closest('.hexagon-cell');
        if (!hex) return;
        
        const dateStr = hex.dataset.date;
        const status = hex.dataset.status;
        const concluido = hex.dataset.concluido === 'true';
        
        const statusBadge = concluido 
            ? `<span style="color: var(--success-color); font-weight: 600;">✓ ${status}</span>`
            : `<span style="color: var(--text-secondary); font-weight: 600;">✗ ${status}</span>`;
            
        tooltip.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 2px;">${dateStr}</div>
            <div>${statusBadge}</div>
        `;
        
        tooltip.classList.add('show');
    });
    
    newContainer.addEventListener('mousemove', (event) => {
        // Posicionamento absoluto baseado no viewport
        tooltip.style.left = `${event.clientX}px`;
        tooltip.style.top = `${event.clientY}px`;
    });
    
    newContainer.addEventListener('mouseout', (event) => {
        if (event.target.closest('.hexagon-cell')) {
            tooltip.classList.remove('show');
        }
    });
}
