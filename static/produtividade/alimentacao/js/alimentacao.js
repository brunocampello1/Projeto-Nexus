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
        const dataCal = graficoCaloriasData.map(d => d.y);

        new Chart(ctxCal, {
            type: 'bar',
            data: {
                labels: labelsCal,
                datasets: [{
                    label: 'Calorias Consumidas',
                    data: dataCal,
                    backgroundColor: '#10B981', // success-color from nexus
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { ticks: { color: textColor }, grid: { display: false } },
                    y: { ticks: { color: textColor }, grid: { color: gridColor } }
                }
            }
        });
    }

    // Theme toggle observer: if theme changes, we should ideally re-render charts, 
    // but a page reload is often triggered or we can just leave it as is for now.
});
