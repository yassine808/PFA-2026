document.addEventListener('DOMContentLoaded', () => {
    const barData = window.barData;
    const stackData = window.stackData;
    const initialKPIs = window.initialKPIs || {};

    // Get ALL KPI elements
    const avgRatingEl = document.getElementById("avgRating");
    const satisfactionEl = document.getElementById("satisfaction");
    const totalReviewsEl = document.getElementById("totalReviews");
    const changeEl = document.getElementById("change");
    const avgPlaytimeEl = document.getElementById("avgPlaytime");
    const helpfulReviewsEl = document.getElementById("helpfulReviews");
    const steamPurchaseEl = document.getElementById("steamPurchase");
    const earlyAccessEl = document.getElementById("earlyAccess");

    // Initialize with backend data for ALL games
    updateKPIs(initialKPIs);

    // Initialize charts
    const ctxBar = document.getElementById('barChart').getContext('2d');
    const ctxStack = document.getElementById('stackChart').getContext('2d');

    const barChart = new Chart(ctxBar, {
        type: 'bar',
        data: { 
            labels: [], 
            datasets: [{ 
                label: 'Reviews per Game', 
                data: [], 
                backgroundColor: 'rgba(255,88,88,0.7)',
                borderRadius: 5
            }] 
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false, 
            plugins: { legend: { display: false } }, 
            scales: { 
                y: { 
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.1)' }
                },
                x: {
                    grid: { color: 'rgba(255,255,255,0.1)' }
                }
            } 
        }
    });

    const stackChart = new Chart(ctxStack, {
        type: 'bar',
        data: { 
            labels: [], 
            datasets: [
                { 
                    label: 'Recommended', 
                    data: [], 
                    backgroundColor: 'rgba(0,200,255,0.7)',
                    borderRadius: 5
                },
                { 
                    label: 'Not Recommended', 
                    data: [], 
                    backgroundColor: 'rgba(255,165,0,0.7)',
                    borderRadius: 5
                }
            ] 
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false, 
            scales: { 
                x: { 
                    stacked: true,
                    grid: { color: 'rgba(255,255,255,0.1)' }
                }, 
                y: { 
                    stacked: true, 
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.1)' }
                } 
            },
            plugins: {
                legend: {
                    labels: { color: '#fff' }
                }
            }
        }
    });

    // Function to update all KPIs
    function updateKPIs(kpis) {
        console.log("Updating KPIs with:", kpis);
        
        avgRatingEl.textContent = kpis.avgRating !== undefined && kpis.avgRating !== '--' ? `${kpis.avgRating} ★` : '--';
        satisfactionEl.textContent = kpis.satisfaction !== undefined && kpis.satisfaction !== '--' ? `${kpis.satisfaction}%` : '--%';
        totalReviewsEl.textContent = kpis.totalReviews && kpis.totalReviews !== '--' ? kpis.totalReviews : '--';
        changeEl.textContent = kpis.change && kpis.change !== '--' ? kpis.change : '+4.2%';
        avgPlaytimeEl.textContent = kpis.avgPlaytimeHours !== undefined && kpis.avgPlaytimeHours !== '--' ? `${kpis.avgPlaytimeHours}h` : '--h';
        helpfulReviewsEl.textContent = kpis.helpfulReviewsPct !== undefined && kpis.helpfulReviewsPct !== '--' ? `${kpis.helpfulReviewsPct}%` : '--%';
        steamPurchaseEl.textContent = kpis.steamPurchasePct !== undefined && kpis.steamPurchasePct !== '--' ? `${kpis.steamPurchasePct}%` : '--%';
        earlyAccessEl.textContent = kpis.earlyAccessPct !== undefined && kpis.earlyAccessPct !== '--' ? `${kpis.earlyAccessPct}%` : '--%';
    }

    // Function to fetch KPIs from API
    function fetchKPIs(gameName = 'all') {
        console.log(`Fetching KPIs for: ${gameName}`);
        
        fetch(`/api/kpis/${encodeURIComponent(gameName)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(kpis => {
                console.log(`Received KPIs for ${gameName}:`, kpis);
                updateKPIs(kpis);
            })
            .catch(error => {
                console.error('Error fetching KPIs:', error);
                // If fetching specific game fails, revert to all games KPIs
                if (gameName !== 'all') {
                    updateKPIs(initialKPIs);
                }
            });
    }

    function updateDashboard(filter = 'all') {
        console.log(`Updating dashboard with filter: ${filter}`);
        
        // Filter chart data
        const filteredBar = filter === 'all' ? barData : barData.filter(d => d.app_name.toLowerCase() === filter.toLowerCase());
        const filteredStack = filter === 'all' ? stackData : stackData.filter(d => d.app_name.toLowerCase() === filter.toLowerCase());

        // Always fetch KPIs from API
        fetchKPIs(filter);

        // Update bar chart
        barChart.data.labels = filteredBar.map(d => d.app_name);
        barChart.data.datasets[0].data = filteredBar.map(d => d.review_count);
        barChart.update();

        // Update stacked chart
        const appsFiltered = [...new Set(filteredStack.map(d => d.app_name))];
        stackChart.data.labels = appsFiltered;
        stackChart.data.datasets[0].data = appsFiltered.map(app => {
            const entry = filteredStack.find(d => d.app_name === app && d.recommended);
            return entry ? entry.count : 0;
        });
        stackChart.data.datasets[1].data = appsFiltered.map(app => {
            const entry = filteredStack.find(d => d.app_name === app && !d.recommended);
            return entry ? entry.count : 0;
        });
        stackChart.update();
    }

    // Search functionality
    const searchInput = document.getElementById('gameSearch');
    const suggestionsContainer = document.getElementById('gameSuggestions');
    const resetBtn = document.getElementById('resetFilter');
    const gameNames = barData.map(d => d.app_name);

    searchInput.addEventListener('input', () => {
        const value = searchInput.value.toLowerCase();
        suggestionsContainer.innerHTML = '';
        if (!value) {
            suggestionsContainer.style.display = 'none';
            return;
        }

        const filtered = gameNames.filter(g => g.toLowerCase().includes(value));
        filtered.forEach(g => {
            const div = document.createElement('div');
            div.textContent = g;
            div.className = 'suggestion-item';
            div.addEventListener('click', () => {
                searchInput.value = g;
                suggestionsContainer.style.display = 'none';
                updateDashboard(g);
            });
            suggestionsContainer.appendChild(div);
        });
        suggestionsContainer.style.display = filtered.length ? 'block' : 'none';
    });

    searchInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            const searchTerm = searchInput.value.trim();
            updateDashboard(searchTerm || 'all');
        }
    });

    document.addEventListener('click', e => {
        if (!searchInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
            suggestionsContainer.style.display = 'none';
        }
    });

    resetBtn.addEventListener('click', () => {
        console.log("Reset button clicked");
        searchInput.value = '';
        suggestionsContainer.style.display = 'none';
        updateDashboard('all');
    });

    // Initial load
    updateDashboard('all');
});

