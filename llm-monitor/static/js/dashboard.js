/**
 * LLM Monitor Dashboard — Client-side JavaScript
 * Handles WebSocket connection, REST API polling, and table rendering.
 */

(function () {
    "use strict";

    // ── Configuration ──
    const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
    const API_BASE = "/api/metrics";
    const REFRESH_INTERVAL = 10000;

    // ── State ──
    let ws = null;
    let wsReconnectDelay = 1000;
    let refreshTimer = null;
    let currentSort = { column: "timestamp", direction: "desc" };
    let dateRange = "today";
    let selectedModel = "";

    // ── Date helpers ──
    function getDateRange() {
        const now = new Date();
        let from, to;
        switch (dateRange) {
            case "today":
                from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                to = now;
                break;
            case "7d":
                from = new Date(now - 7 * 24 * 60 * 60 * 1000);
                to = now;
                break;
            case "30d":
                from = new Date(now - 30 * 24 * 60 * 60 * 1000);
                to = now;
                break;
            case "custom":
                from = document.getElementById("date-from").value ? new Date(document.getElementById("date-from").value) : null;
                to = document.getElementById("date-to").value ? new Date(document.getElementById("date-to").value) : now;
                break;
            default:
                from = null;
                to = now;
        }
        return { from: from ? from.toISOString() : null, to: to.toISOString() };
    }

    // ── API helpers ──
    async function fetchJSON(url) {
        try {
            const resp = await fetch(url);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (err) {
            console.error(`API error: ${url}`, err);
            return null;
        }
    }

    async function loadSummary() {
        const { from, to } = getDateRange();
        const params = new URLSearchParams();
        if (from) params.set("from", from);
        if (to) params.set("to", to);

        const data = await fetchJSON(`${API_BASE}/summary?${params}`);
        if (!data) return;

        document.getElementById("card-requests").textContent = data.total_requests || "0";
        document.getElementById("card-latency").textContent =
            data.avg_latency_ms ? `${(data.avg_latency_ms / 1000).toFixed(1)}s` : "—";
        document.getElementById("card-tokens").textContent =
            formatNumber(data.total_all_tokens || 0);
        document.getElementById("card-success").textContent =
            data.success_rate != null ? `${data.success_rate}%` : "—";
        document.getElementById("card-prompt-tps").textContent =
            data.avg_prompt_tps != null ? `${data.avg_prompt_tps.toFixed(1)}` : "—";
        document.getElementById("card-gen-tps").textContent =
            data.avg_generation_tps != null ? `${data.avg_generation_tps.toFixed(1)}` : "—";

        if (!data.gpu_available) {
            document.getElementById("card-gpu-container").style.display = "none";
        }
    }

    async function loadModels() {
        const data = await fetchJSON(`${API_BASE}/models`);
        if (!data) return;

        const select = document.getElementById("model-filter");
        const current = select.value;
        select.innerHTML = '<option value="">All Models</option>';
        data.models.forEach((m) => {
            const opt = document.createElement("option");
            opt.value = m;
            opt.textContent = m;
            select.appendChild(opt);
        });
        select.value = current || "";
    }

    async function loadRequests() {
        const { from, to } = getDateRange();
        const params = new URLSearchParams();
        if (from) params.set("from", from);
        if (to) params.set("to", to);
        if (selectedModel) params.set("model", selectedModel);
        params.set("limit", "100");

        const data = await fetchJSON(`${API_BASE}/requests?${params}`);
        if (!data) return;

        updateRequestsTable(data.requests || []);
    }

    async function loadSystemMetrics() {
        const { from, to } = getDateRange();
        const params = new URLSearchParams();
        if (from) params.set("from", from);
        if (to) params.set("to", to);

        const data = await fetchJSON(`${API_BASE}/system?${params}`);
        if (!data) return;

        const sorted = [...data.metrics].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        if (sorted.length > 0) {
            const latest = sorted[0];
            if (latest.gpu_utilization != null) {
                document.getElementById("card-gpu").textContent = `${latest.gpu_utilization.toFixed(1)}%`;
            }
            if (latest.cpu_usage != null) {
                document.getElementById("card-cpu").textContent = `${latest.cpu_usage.toFixed(1)}%`;
            }
        }
    }

    // ── Table ──
    function updateRequestsTable(requests) {
        const tbody = document.getElementById("requests-tbody");
        tbody.innerHTML = "";

        const sorted = [...requests].sort((a, b) => {
            const col = currentSort.column;
            const dir = currentSort.direction === "asc" ? 1 : -1;
            const aVal = a[col] ?? "";
            const bVal = b[col] ?? "";
            if (typeof aVal === "string") return aVal.localeCompare(bVal) * dir;
            return ((aVal || 0) - (bVal || 0)) * dir;
        });

        sorted.forEach((r) => {
            const tr = document.createElement("tr");
            const statusClass = r.status_code === 200 ? "status-200" : "status-error";
            tr.innerHTML = `
                <td>${formatTime(r.timestamp)}</td>
                <td>${r.model || "—"}</td>
                <td>${r.endpoint || "—"}</td>
                <td class="${statusClass}">${r.status_code || "—"}</td>
                <td>${r.prompt_tokens || 0}</td>
                <td>${r.completion_tokens || 0}</td>
                <td>${r.prompt_tokens_per_second ? r.prompt_tokens_per_second.toFixed(1) : "—"}</td>
                <td>${r.generation_tokens_per_second ? r.generation_tokens_per_second.toFixed(1) : "—"}</td>
                <td>${r.total_latency_ms ? (r.total_latency_ms / 1000).toFixed(2) + "s" : "—"}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // ── WebSocket ──
    function connectWebSocket() {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            wsReconnectDelay = 1000;
            setStatus("online");
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === "request_metric") {
                    loadSummary();
                    loadRequests();
                } else if (msg.type === "system_metric") {
                    const data = msg.data;
                    if (data.gpu_utilization != null) {
                        document.getElementById("card-gpu").textContent = `${data.gpu_utilization.toFixed(1)}%`;
                    }
                    if (data.cpu_usage != null) {
                        document.getElementById("card-cpu").textContent = `${data.cpu_usage.toFixed(1)}%`;
                    }
                }
            } catch (err) {
                console.error("WebSocket parse error:", err);
            }
        };

        ws.onclose = () => {
            setStatus("offline");
            setTimeout(connectWebSocket, wsReconnectDelay);
            wsReconnectDelay = Math.min(wsReconnectDelay * 2, 30000);
        };

        ws.onerror = () => ws.close();
    }

    // ── Status indicator ──
    function setStatus(status) {
        const el = document.getElementById("connection-status");
        el.className = `status-indicator ${status}`;
        el.querySelector(".status-text").textContent = status === "online" ? "Live" : "Offline";
    }

    // ── Formatting ──
    function formatNumber(n) {
        if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
        if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
        return n.toString();
    }

    function formatTime(iso) {
        if (!iso) return "—";
        return new Date(iso).toLocaleTimeString();
    }

    // ── Full refresh ──
    async function fullRefresh() {
        await Promise.all([
            loadSummary(),
            loadRequests(),
            loadSystemMetrics(),
        ]);
    }

    // ── Event handlers ──
    function setupEvents() {
        document.getElementById("date-range").addEventListener("change", (e) => {
            dateRange = e.target.value;
            const fromInput = document.getElementById("date-from");
            const toInput = document.getElementById("date-to");
            if (dateRange === "custom") {
                fromInput.classList.remove("hidden");
                toInput.classList.remove("hidden");
            } else {
                fromInput.classList.add("hidden");
                toInput.classList.add("hidden");
            }
        });

        document.getElementById("model-filter").addEventListener("change", (e) => {
            selectedModel = e.target.value;
        });

        document.getElementById("apply-filters").addEventListener("click", () => {
            fullRefresh();
        });

        document.querySelectorAll("th[data-sort]").forEach((th) => {
            th.addEventListener("click", () => {
                const col = th.dataset.sort;
                if (currentSort.column === col) {
                    currentSort.direction = currentSort.direction === "asc" ? "desc" : "asc";
                } else {
                    currentSort.column = col;
                    currentSort.direction = "desc";
                }
                loadRequests();
            });
        });
    }

    // ── Init ──
    async function init() {
        setupEvents();
        await loadModels();
        await fullRefresh();
        connectWebSocket();
        refreshTimer = setInterval(fullRefresh, REFRESH_INTERVAL);

        setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send("ping");
            }
        }, 30000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
