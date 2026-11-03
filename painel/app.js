(() => {
  "use strict";

  const WS_PROTOCOL = window.location.protocol === "https:" ? "wss:" : "ws:";
  const MAX_READINGS = 50;
  const MAX_TABLE_ROWS = 8;
  const MAX_ALERT_ROWS = 10;
  const readings = [];
  const alerts = [];
  const pendingLiveReadings = [];
  const knownMetrics = new Set();
  const knownDevices = new Set();
  let receivedCount = 0;
  let historyLoaded = false;

  const elements = {
    connection: document.querySelector(".connection-status"),
    connectionLabel: document.getElementById("connection-label"),
    serverStatus: document.getElementById("server-status"),
    serverUptime: document.getElementById("server-uptime"),
    activeConnections: document.getElementById("active-connections"),
    readingCount: document.getElementById("reading-count"),
    lastUpdated: document.getElementById("last-updated"),
    metricFilter: document.getElementById("metric-filter"),
    deviceFilter: document.getElementById("device-filter"),
    readingsList: document.getElementById("readings-list"),
    alertsList: document.getElementById("alerts-list"),
    alertsCount: document.getElementById("alerts-count"),
    chartCanvas: document.getElementById("readings-chart"),
    chartEmpty: document.getElementById("chart-empty"),
    apiAddress: document.getElementById("api-address"),
  };

  elements.apiAddress.textContent = `API via painel: ${window.location.host}`;

  let chart = null;
  if (window.Chart) {
    chart = new Chart(elements.chartCanvas, {
      type: "line",
      data: { labels: [], datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { intersect: false, mode: "index" },
        plugins: {
          legend: {
            display: true,
            labels: { color: "#a9b8bf", boxWidth: 8, usePointStyle: true, font: { size: 10 } },
          },
          tooltip: {
            backgroundColor: "#101a22",
            borderColor: "#2a3a44",
            borderWidth: 1,
            titleColor: "#e8f0f3",
            bodyColor: "#c5d1d6",
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(42, 58, 68, 0.45)" },
            ticks: { color: "#82949d", maxTicksLimit: 7, maxRotation: 0, font: { size: 9 } },
            border: { display: false },
          },
          y: {
            grid: { color: "rgba(42, 58, 68, 0.6)" },
            ticks: { color: "#82949d", font: { size: 9 } },
            border: { display: false },
          },
        },
      },
    });
  } else {
    elements.chartEmpty.querySelector("strong").textContent = "Não foi possível carregar o gráfico";
    elements.chartEmpty.querySelector("span:last-child").textContent = "Verifique sua conexão com a internet para carregar o Chart.js.";
  }

  function setConnectionState(state, label) {
    elements.connection.classList.toggle("connected", state === "connected");
    elements.connection.classList.toggle("disconnected", state === "disconnected");
    elements.connectionLabel.textContent = label;
  }

  function formatUptime(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const remainder = total % 60;
    if (hours > 0) return `${hours}h ${minutes}min de atividade`;
    if (minutes > 0) return `${minutes}min ${remainder}s de atividade`;
    return `${remainder}s de atividade`;
  }

  async function updateServerStatus() {
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      if (!response.ok) throw new Error(`API respondeu com HTTP ${response.status}`);
      const status = await response.json();
      elements.serverStatus.textContent = status.status === "online" ? "Online" : "Indisponível";
      elements.serverStatus.classList.toggle("offline", status.status !== "online");
      elements.serverUptime.textContent = Number.isFinite(status.uptime_segundos)
        ? formatUptime(status.uptime_segundos)
        : "Status da API recebido";
      elements.activeConnections.textContent = Number.isFinite(status.sensores_conectados)
        ? String(status.sensores_conectados)
        : "—";
    } catch (error) {
      elements.serverStatus.textContent = "Offline";
      elements.serverStatus.classList.add("offline");
      elements.serverUptime.textContent = "Não foi possível acessar a API";
      elements.activeConnections.textContent = "—";
      console.error("Falha ao consultar o status do servidor:", error);
    }
  }

  function addFilterOption(select, value, label) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  }

  function registerFilterValues(reading) {
    if (reading.metrica && !knownMetrics.has(reading.metrica)) {
      knownMetrics.add(reading.metrica);
      addFilterOption(elements.metricFilter, reading.metrica, reading.metrica);
    }
    if (reading.device_id && !knownDevices.has(reading.device_id)) {
      knownDevices.add(reading.device_id);
      addFilterOption(elements.deviceFilter, reading.device_id, reading.device_id);
    }
  }

  function displayTimestamp(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? new Date().toLocaleTimeString("pt-BR")
      : date.toLocaleTimeString("pt-BR");
  }

  function renderReadings() {
    const metric = elements.metricFilter.value;
    const device = elements.deviceFilter.value;
    const filtered = readings.filter((reading) => (
      (metric === "all" || reading.metrica === metric)
      && (device === "all" || reading.device_id === device)
    ));

    elements.chartEmpty.hidden = filtered.length > 0;
    if (!chart) return;

    const series = [...new Set(filtered.map((reading) => `${reading.device_id} · ${reading.metrica}`))];
    const colors = ["#53d6c3", "#9db5ff", "#ffc574", "#e79bff", "#ff8e83", "#8ddc8d"];
    const labels = filtered.map((reading) => displayTimestamp(reading.timestamp));
    chart.data.labels = labels;
    chart.data.datasets = series.map((label, index) => {
      const color = colors[index % colors.length];
      return {
        label,
        data: filtered.map((reading) => (
          `${reading.device_id} · ${reading.metrica}` === label ? Number(reading.valor) : null
        )),
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        pointRadius: filtered.length > 30 ? 0 : 2,
        pointHoverRadius: 4,
        tension: 0.32,
        spanGaps: true,
      };
    });
    chart.update("none");
  }

  function renderTable() {
    // readings fica em ordem crescente; a tabela mostra as mais recentes primeiro.
    const rows = readings.slice(-MAX_TABLE_ROWS).reverse();
    elements.readingsList.replaceChildren();

    if (rows.length === 0) {
      const row = document.createElement("tr");
      row.className = "empty-row";
      const cell = document.createElement("td");
      cell.colSpan = 3;
      cell.textContent = "Nenhuma leitura recebida ainda.";
      row.append(cell);
      elements.readingsList.append(row);
      return;
    }

    rows.forEach((reading) => {
      const row = document.createElement("tr");
      const sensorCell = document.createElement("td");
      const valueCell = document.createElement("td");
      const timeCell = document.createElement("td");
      sensorCell.textContent = `${reading.device_id} / ${reading.metrica}`;
      // O protocolo usa "C" para temperatura; na tela exibimos "°C".
      const unit = reading.unidade === "C" ? "°C" : reading.unidade;
      valueCell.textContent = `${reading.valor} ${unit || ""}`.trim();
      timeCell.textContent = displayTimestamp(reading.timestamp);
      row.append(sensorCell, valueCell, timeCell);
      elements.readingsList.append(row);
    });
  }

  function handleReading(message) {
    if (message.tipo === "alerta") {
      handleAlert(message);
      return;
    }

    if (
      message.tipo !== "update"
      || typeof message.device_id !== "string"
      || typeof message.metrica !== "string"
      || typeof message.valor !== "number"
    ) {
      console.warn("Mensagem de atualização recebida em formato inesperado:", message);
      return;
    }

    const reading = {
      id: Number.isInteger(message.id) ? message.id : null,
      device_id: message.device_id,
      metrica: message.metrica,
      valor: message.valor,
      unidade: typeof message.unidade === "string" ? message.unidade : "",
      timestamp: message.timestamp || new Date().toISOString(),
    };

    receivedCount += 1;
    elements.readingCount.textContent = String(receivedCount);

    if (!historyLoaded) {
      pendingLiveReadings.push(reading);
      return;
    }

    appendReading(reading);
  }

  function alertKey(alert) {
    return [
      alert.device_id,
      alert.metrica,
      alert.valor,
      alert.limiar,
      alert.nivel,
      alert.timestamp,
    ].join("|");
  }

  function handleAlert(message) {
    if (
      !["temperatura", "umidade"].includes(message.metrica)
      || typeof message.device_id !== "string"
      || typeof message.valor !== "number"
      || typeof message.limiar !== "number"
    ) {
      console.warn("Alerta recebido em formato inesperado:", message);
      return;
    }

    const alert = {
      device_id: message.device_id,
      metrica: message.metrica,
      valor: message.valor,
      limiar: message.limiar,
      nivel: typeof message.nivel === "string" ? message.nivel : "alerta",
      timestamp: message.timestamp || new Date().toISOString(),
    };

    if (alerts.some((item) => alertKey(item) === alertKey(alert))) return;
    alerts.push(alert);
    alerts.sort((first, second) => new Date(second.timestamp) - new Date(first.timestamp));
    renderAlerts();
  }

  function renderAlerts(message = "Nenhum alerta de temperatura ou umidade.") {
    const rows = alerts.slice(0, MAX_ALERT_ROWS);
    elements.alertsList.replaceChildren();
    elements.alertsCount.textContent = `${alerts.length} ${alerts.length === 1 ? "alerta" : "alertas"}`;

    if (rows.length === 0) {
      const row = document.createElement("tr");
      row.className = "empty-row";
      const cell = document.createElement("td");
      cell.colSpan = 5;
      cell.textContent = message;
      row.append(cell);
      elements.alertsList.append(row);
      return;
    }

    rows.forEach((alert) => {
      const row = document.createElement("tr");
      row.className = "alert-row";
      const sensorCell = document.createElement("td");
      const valueCell = document.createElement("td");
      const thresholdCell = document.createElement("td");
      const levelCell = document.createElement("td");
      const timeCell = document.createElement("td");
      const unit = alert.metrica === "temperatura" ? "°C" : "%";

      sensorCell.textContent = `${alert.device_id} / ${alert.metrica}`;
      valueCell.textContent = `${alert.valor} ${unit}`;
      thresholdCell.textContent = `${alert.limiar} ${unit}`;
      levelCell.textContent = alert.nivel;
      timeCell.textContent = displayTimestamp(alert.timestamp);
      row.append(sensorCell, valueCell, thresholdCell, levelCell, timeCell);
      elements.alertsList.append(row);
    });
  }

  async function loadAlerts() {
    try {
      const response = await fetch("/api/alertas", { cache: "no-store" });
      if (!response.ok) throw new Error(`API respondeu com HTTP ${response.status}`);
      const history = await response.json();
      if (!Array.isArray(history)) throw new Error("A API retornou alertas em formato inválido");

      history.forEach(handleAlert);
      renderAlerts();
    } catch (error) {
      renderAlerts("Não foi possível carregar os alertas.");
      console.error("Falha ao carregar o histórico de alertas:", error);
    }
  }

  function appendReading(reading) {
    if (reading.id !== null && readings.some((item) => item.id === reading.id)) return;
    readings.push(reading);
    readings.sort((first, second) => {
      if (first.id !== null && second.id !== null) return first.id - second.id;
      return new Date(first.timestamp) - new Date(second.timestamp);
    });
    if (readings.length > MAX_READINGS) readings.shift();
    registerFilterValues(reading);
    elements.lastUpdated.textContent = new Date(readings[readings.length - 1].timestamp)
      .toLocaleString("pt-BR");
    renderReadings();
    renderTable();
  }

  async function loadHistory() {
    try {
      const response = await fetch(`/api/leituras?limite=${MAX_READINGS}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`API respondeu com HTTP ${response.status}`);
      const history = await response.json();
      if (!Array.isArray(history)) throw new Error("A API retornou um histórico em formato inválido");

      history.reverse().forEach((reading) => {
        if (
          typeof reading.device_id !== "string"
          || typeof reading.metrica !== "string"
          || typeof reading.valor !== "number"
        ) {
          console.warn("Leitura histórica ignorada por estar em formato inesperado:", reading);
          return;
        }
        readings.push({
          id: Number.isInteger(reading.id) ? reading.id : null,
          device_id: reading.device_id,
          metrica: reading.metrica,
          valor: reading.valor,
          unidade: typeof reading.unidade === "string" ? reading.unidade : "",
          timestamp: reading.timestamp || new Date().toISOString(),
        });
      });

      historyLoaded = true;
      pendingLiveReadings.forEach(appendReading);
      pendingLiveReadings.length = 0;
      readings.slice(-MAX_READINGS).forEach(registerFilterValues);
      readings.splice(0, Math.max(0, readings.length - MAX_READINGS));
      if (readings.length > 0) {
        elements.lastUpdated.textContent = new Date(readings[readings.length - 1].timestamp)
          .toLocaleString("pt-BR");
      }
      renderReadings();
      renderTable();
    } catch (error) {
      historyLoaded = true;
      pendingLiveReadings.forEach(appendReading);
      pendingLiveReadings.length = 0;
      console.error("Falha ao carregar o histórico de leituras:", error);
    }
  }

  function connectWebSocket() {
    setConnectionState("connecting", "Conectando ao fluxo de dados...");
    const socket = new WebSocket(`${WS_PROTOCOL}//${window.location.host}/ws/painel`);

    socket.addEventListener("open", () => {
      setConnectionState("connected", "Recebendo dados em tempo real");
    });

    socket.addEventListener("message", (event) => {
      try {
        handleReading(JSON.parse(event.data));
      } catch (error) {
        console.error("Não foi possível interpretar uma mensagem do servidor:", error);
      }
    });

    socket.addEventListener("error", () => {
      setConnectionState("disconnected", "Falha na conexão com o servidor");
    });

    socket.addEventListener("close", () => {
      setConnectionState("disconnected", "Conexão perdida; tentando novamente...");
      window.setTimeout(connectWebSocket, 3000);
    });
  }

  elements.metricFilter.addEventListener("change", renderReadings);
  elements.deviceFilter.addEventListener("change", renderReadings);

  updateServerStatus();
  window.setInterval(updateServerStatus, 10000);
  connectWebSocket();
  loadHistory();
  loadAlerts();
})();
