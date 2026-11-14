
// ============================================================
// SUPPLY CHAIN OPTIMIZATION DASHBOARD
// Complete Dashboard + Sidebar Navigation
// ============================================================

let demandChart = null;
let inventoryChart = null;


// ============================================================
// HELPERS
// ============================================================

function formatNumber(value) {
    return Number(value || 0).toLocaleString("en-IN", {
        maximumFractionDigits: 2
    });
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}


// ============================================================
// DATE
// ============================================================

function updateDate() {
    const dateElement = document.getElementById("currentDate");

    if (dateElement) {
        dateElement.textContent = new Date().toLocaleDateString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );
    }
}


// ============================================================
// KPI CARDS
// ============================================================

function updateMetrics(metrics) {

    const totalSkus = document.getElementById("totalSkus");
    const totalLocations = document.getElementById("totalLocations");
    const totalSuppliers = document.getElementById("totalSuppliers");
    const totalShortages = document.getElementById("totalShortages");

    if (totalSkus) {
        totalSkus.textContent = formatNumber(metrics.total_skus);
    }

    if (totalLocations) {
        totalLocations.textContent = formatNumber(metrics.total_locations);
    }

    if (totalSuppliers) {
        totalSuppliers.textContent = formatNumber(metrics.total_suppliers);
    }

    if (totalShortages) {
        totalShortages.textContent = formatNumber(metrics.total_shortages);
    }
}


// ============================================================
// DEMAND FORECAST CHART
// ============================================================

function createDemandChart(chartData) {

    const canvas = document.getElementById("demandChart");
    const placeholder = document.getElementById("demandPlaceholder");

    if (!canvas || !window.Chart || !chartData) {
        return;
    }

    if (demandChart) {
        demandChart.destroy();
    }

    demandChart = new Chart(canvas, {
        type: "line",

        data: {
            labels: chartData.labels || [],

            datasets: [{
                label: "Forecast Demand",
                data: chartData.values || [],

                borderColor: "#1769aa",
                backgroundColor: "rgba(23, 105, 170, 0.12)",

                borderWidth: 2,
                fill: true,
                tension: 0.35,

                pointRadius: 2,
                pointHoverRadius: 5
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    display: true,
                    position: "top"
                }
            },

            scales: {
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    }
                },

                y: {
                    beginAtZero: true
                }
            }
        }
    });

    if (placeholder) {
        placeholder.style.display = "none";
    }
}


// ============================================================
// INVENTORY CHART
// ============================================================

function createInventoryChart(chartData) {

    const canvas = document.getElementById("inventoryChart");
    const placeholder = document.getElementById("inventoryPlaceholder");

    if (!canvas || !window.Chart || !chartData) {
        return;
    }

    if (inventoryChart) {
        inventoryChart.destroy();
    }

    inventoryChart = new Chart(canvas, {
        type: "doughnut",

        data: {
            labels: chartData.labels || [],

            datasets: [{
                data: chartData.values || [],

                backgroundColor: [
                    "#1769aa",
                    "#f0a44b"
                ],

                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });

    if (placeholder) {
        placeholder.style.display = "none";
    }
}


// ============================================================
// SHORTAGE TABLE
// ============================================================

function updateShortageTable(shortages) {

    const table = document.getElementById("shortageTable");

    if (!table) {
        return;
    }

    if (!shortages || shortages.length === 0) {

        table.innerHTML = `
            <tr>
                <td colspan="5" class="empty-message">
                    No projected shortage records found.
                </td>
            </tr>
        `;

        return;
    }

    table.innerHTML = shortages.map(item => `
        <tr>
            <td>${escapeHTML(item.sku_id)}</td>
            <td>${escapeHTML(item.location_id)}</td>
            <td>${escapeHTML(item.week)}</td>
            <td>${formatNumber(item.quantity)}</td>
            <td>${escapeHTML(item.status)}</td>
        </tr>
    `).join("");
}


// ============================================================
// PRODUCTION SUMMARY
// ============================================================

function updateProduction(metrics) {

    const productionPanel = document.querySelector(
        "#production .info-placeholder p"
    );

    if (productionPanel) {

        productionPanel.textContent =
            "Planned production: " +
            formatNumber(metrics.planned_production) +
            " | Total capacity: " +
            formatNumber(metrics.production_capacity);
    }
}


// ============================================================
// NAVIGATION
// ============================================================

function setupNavigation() {

    const main = document.querySelector(".main-content");

    if (!main) {
        return;
    }

    const footer = document.querySelector(".main-footer");

    const welcome = document.querySelector(".welcome-section");
    const sectionHeading = document.querySelector(".section-heading");
    const kpiGrid = document.querySelector(".kpi-grid");

    const demandPanel = document.getElementById("demand");
    const inventoryPanel = document.getElementById("inventory");
    const shortagesPanel = document.getElementById("shortages");
    const productionPanel = document.getElementById("production");
    const mitigationPanel = document.getElementById("mitigation");

    const chartsGrid = document.querySelector(".charts-grid");
    const bottomGrid = document.querySelector(".bottom-grid");

    const title = main.querySelector(".topbar h1");
    const subtitle = main.querySelector(".topbar p");

    const navigationLinks = document.querySelectorAll(".nav-link");

    // Check that all required HTML sections exist
    if (
        !welcome ||
        !sectionHeading ||
        !kpiGrid ||
        !demandPanel ||
        !inventoryPanel ||
        !shortagesPanel ||
        !productionPanel ||
        !mitigationPanel ||
        !footer
    ) {
        console.error("Navigation setup failed: HTML section missing.");
        return;
    }

    // Create page container
    const pageContainer = document.createElement("div");
    pageContainer.className = "page-container";

    // Create individual pages
    const pages = {};

    const pageNames = [
        "dashboard",
        "inventory",
        "demand",
        "shortages",
        "production",
        "mitigation"
    ];

    pageNames.forEach(name => {

        const page = document.createElement("section");

        page.className = "page-view";
        page.id = "page-" + name;

        pages[name] = page;

        pageContainer.appendChild(page);
    });

    // Dashboard page
    pages.dashboard.appendChild(welcome);
    pages.dashboard.appendChild(sectionHeading);
    pages.dashboard.appendChild(kpiGrid);

    // Inventory page
    pages.inventory.appendChild(inventoryPanel);

    // Demand Forecast page
    pages.demand.appendChild(demandPanel);

    // Shortages page
    pages.shortages.appendChild(shortagesPanel);

    // Production Planning page
    pages.production.appendChild(productionPanel);

    // Mitigation page
    pages.mitigation.appendChild(mitigationPanel);

    // Remove empty layout wrappers
    if (chartsGrid) {
        chartsGrid.remove();
    }

    if (bottomGrid) {
        bottomGrid.remove();
    }

    // Insert pages before footer
    main.insertBefore(pageContainer, footer);

    // Page headings
    const pageDetails = {

        dashboard: {
            title: "Dashboard",
            subtitle: "Supply chain performance overview"
        },

        inventory: {
            title: "Inventory",
            subtitle: "Inventory status and availability overview"
        },

        demand: {
            title: "Demand Forecast",
            subtitle: "Weekly forecast demand analysis"
        },

        shortages: {
            title: "Shortages",
            subtitle: "Projected shortage records"
        },

        production: {
            title: "Production Planning",
            subtitle: "Production plans and capacity information"
        },

        mitigation: {
            title: "Mitigation",
            subtitle: "Shortage resolution recommendations"
        }
    };


    // Show selected page
    function showPage(pageName) {

        if (!pages[pageName]) {
            pageName = "dashboard";
        }

        // Hide all pages
        Object.values(pages).forEach(page => {
            page.classList.remove("active");
        });

        // Display selected page
        pages[pageName].classList.add("active");

        // Update page title
        if (title) {
            title.textContent = pageDetails[pageName].title;
        }

        if (subtitle) {
            subtitle.textContent = pageDetails[pageName].subtitle;
        }

        // Update active sidebar link
        navigationLinks.forEach(link => {

            const linkPage = link.getAttribute("href").substring(1);

            link.classList.toggle(
                "active",
                linkPage === pageName
            );
        });

        // Update browser URL
        history.replaceState(null, "", "#" + pageName);

        // Scroll to top
        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

        // Resize charts when their page becomes visible
        requestAnimationFrame(() => {

            if (demandChart) {
                demandChart.resize();
            }

            if (inventoryChart) {
                inventoryChart.resize();
            }

        });
    }


    // Sidebar click events
    navigationLinks.forEach(link => {

        link.addEventListener("click", function (event) {

            event.preventDefault();

            const pageName = this.getAttribute("href").substring(1);

            showPage(pageName);

        });

    });


    // Browser back and forward navigation
    window.addEventListener("hashchange", () => {

        const pageName = window.location.hash.substring(1);

        showPage(pageName || "dashboard");

    });


    // Load page based on URL
    const initialPage = window.location.hash.substring(1);

    showPage(initialPage || "dashboard");

}


// ============================================================
// LOAD BACKEND DATA
// ============================================================

async function loadDashboard() {

    try {

        console.log("Loading supply chain dashboard data...");

        const response = await fetch("/api/dashboard");

        if (!response.ok) {
            throw new Error("Dashboard API request failed: " + response.status);
        }

        const result = await response.json();

        if (!result.success) {
            throw new Error(
                result.error || "Unable to load dashboard data."
            );
        }

        const data = result.data;

        updateMetrics(data.metrics);

        createDemandChart(data.demand_chart);

        createInventoryChart(data.inventory_chart);

        updateShortageTable(data.shortages);

        updateProduction(data.metrics);

        console.log("Dashboard data loaded successfully.");

    } catch (error) {

        console.error("Dashboard error:", error);

        const table = document.getElementById("shortageTable");

        if (table) {

            table.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-message">
                        Unable to load dashboard data. Check the Flask server.
                    </td>
                </tr>
            `;
        }
    }
}


// ============================================================
// START APPLICATION
// ============================================================

document.addEventListener("DOMContentLoaded", function () {

    updateDate();

    setupNavigation();

    loadDashboard();

});
