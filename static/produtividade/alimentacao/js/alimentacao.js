document.addEventListener('DOMContentLoaded', function() {
    // Detect theme (dark or light) to color the charts appropriately
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    
    // Variables that match our CSS variables for smooth integration
    const textColor = isDarkMode ? '#F8FAFC' : '#0F172A';
    const gridColor = isDarkMode ? '#1E293B' : '#E2E8F0';
    
    // Gráfico de Peso (Line Chart)
    const ctxPeso = document.getElementById('chartPeso');
    if (ctxPeso && typeof graficoPesoData !== 'undefined') {
        const labelsPeso = graficoPesoData.map(d => d.x);
        const dataPeso = graficoPesoData.map(d => d.y);

        new Chart(ctxPeso, {
            type: 'line',
            data: {
                labels: labelsPeso,
                datasets: [{
                    label: 'Peso (kg)',
                    data: dataPeso,
                    borderColor: '#EF4444', // danger-color from nexus
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    pointBackgroundColor: '#EF4444'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { ticks: { color: textColor }, grid: { color: gridColor } },
                    y: { 
                        ticks: { color: textColor }, 
                        grid: { color: gridColor }
                    }
                }
            }
        });
    }

    // Gráfico de Calorias (Bar Chart)
    const ctxCal = document.getElementById('chartCalorias');
    if (ctxCal && typeof graficoCaloriasData !== 'undefined') {
        const labelsCal = graficoCaloriasData.map(d => d.x);
        const dataDieta = graficoCaloriasData.map(d => d.dieta);
        const dataExtra = graficoCaloriasData.map(d => d.extra);

        const customDataLabelsPlugin = {
            id: 'customDataLabels',
            afterDatasetsDraw(chart, args, options) {
                const {ctx} = chart;
                ctx.save();
                ctx.font = 'bold 11px Inter, sans-serif';
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
                            
                            // Draw internal label
                            ctx.fillStyle = '#FFFFFF';
                            const yCenter = (element.y + element.base) / 2;
                            ctx.fillText(val, element.x, yCenter);
                        }
                    });
                });
                
                // Draw totals on top
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

        new Chart(ctxCal, {
            type: 'bar',
            data: {
                labels: labelsCal,
                datasets: [
                    {
                        label: 'Refeição Planejada',
                        data: dataDieta,
                        backgroundColor: '#10B981',
                        borderRadius: 0
                    },
                    {
                        label: 'Vilões (Extra)',
                        data: dataExtra,
                        backgroundColor: '#EF4444',
                        borderRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        display: true, 
                        position: 'top',
                        labels: { color: textColor, font: { size: 10 } }
                    }
                },
                scales: {
                    x: { 
                        stacked: true, 
                        ticks: { color: textColor }, 
                        grid: { display: false } 
                    },
                    y: { 
                        stacked: true, 
                        ticks: { color: textColor }, 
                        grid: { color: gridColor },
                        // Adicionar um pouco de espaço no topo para o rótulo não cortar
                        grace: '10%'
                    }
                }
            },
            plugins: [customDataLabelsPlugin]
        });
    }

    // Theme toggle observer: if theme changes, we should ideally re-render charts, 
    // but a page reload is often triggered or we can just leave it as is for now.
});
