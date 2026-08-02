"use strict";

const USAGE_API_BASE_URL = "http://127.0.0.1:8002";
const USAGE_PAGE_SIZE = 20;


document.addEventListener(
  "DOMContentLoaded",
  () => {
    const userName =
      document.getElementById("usage-user-name");

    const logoutButton =
      document.getElementById("usage-logout-button");

    const refreshButton =
      document.getElementById("usage-refresh-button");

    const statusFilter =
      document.getElementById("usage-status-filter");

    const modelFilter =
      document.getElementById("usage-model-filter");

    const resultCount =
      document.getElementById("usage-result-count");

    const tableBody =
      document.getElementById("usage-table-body");

    const emptyMessage =
      document.getElementById("usage-empty");

    const errorMessage =
      document.getElementById("usage-error");

    const previousButton =
      document.getElementById("usage-previous-button");

    const nextButton =
      document.getElementById("usage-next-button");

    const pageLabel =
      document.getElementById("usage-page-label");

    const summaryTotalCalls =
      document.getElementById("summary-total-calls");

    const summarySuccessCalls =
      document.getElementById("summary-success-calls");

    const summaryFailedCalls =
      document.getElementById("summary-failed-calls");

    const summaryTotalTokens =
      document.getElementById("summary-total-tokens");

    const summaryTokenSplit =
      document.getElementById("summary-token-split");

    const summaryAverageLatency =
      document.getElementById("summary-average-latency");

    let currentOffset = 0;
    let currentTotal = 0;
    let loading = false;


    function formatNumber(value) {
      return new Intl.NumberFormat("zh-CN").format(
        Number(value || 0)
      );
    }


    function formatDate(value) {
      if (!value) {
        return "—";
      }

      const date = new Date(value);

      if (Number.isNaN(date.getTime())) {
        return value;
      }

      return new Intl.DateTimeFormat(
        "zh-CN",
        {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        }
      ).format(date);
    }


    function formatLatency(value) {
      if (value === null || value === undefined) {
        return "—";
      }

      return `${Number(value).toFixed(3)} 秒`;
    }


    async function readResponseData(response) {
      const text = await response.text();

      if (!text) {
        return {};
      }

      try {
        return JSON.parse(text);
      }
      catch {
        return {
          detail: text
        };
      }
    }


    function extractError(data, fallback) {
      if (
        data &&
        data.detail &&
        typeof data.detail.message === "string"
      ) {
        return data.detail.message;
      }

      if (
        data &&
        typeof data.detail === "string"
      ) {
        return data.detail;
      }

      if (
        data &&
        typeof data.message === "string"
      ) {
        return data.message;
      }

      return fallback;
    }


    async function authenticatedFetch(
      path,
      options = {}
    ) {
      const token =
        UnifiedLlmAuth.getAccessToken();

      if (!token) {
        UnifiedLlmAuth.redirectToLogin();
        throw new Error("请先登录。 ");
      }

      const response = await fetch(
        `${USAGE_API_BASE_URL}${path}`,
        {
          ...options,
          cache: "no-store",
          headers: {
            ...(options.headers || {}),
            "Authorization": `Bearer ${token}`
          }
        }
      );

      const data = await readResponseData(response);

      if (response.status === 401) {
        UnifiedLlmAuth.clearAuthentication();
        UnifiedLlmAuth.redirectToLogin();
        throw new Error("登录状态已失效。 ");
      }

      if (!response.ok) {
        throw new Error(
          extractError(
            data,
            `HTTP ${response.status}`
          )
        );
      }

      return data;
    }


    function showError(message) {
      errorMessage.textContent = message;
      errorMessage.hidden = false;
    }


    function hideError() {
      errorMessage.hidden = true;
      errorMessage.textContent = "";
    }


    function setLoading(value) {
      loading = value;
      refreshButton.disabled = value;
      statusFilter.disabled = value;
      modelFilter.disabled = value;

      refreshButton.textContent = value
        ? "正在加载"
        : "刷新数据";
    }


    function populateModelFilter(models) {
      const selectedValue = modelFilter.value;

      modelFilter.innerHTML =
        '<option value="">全部模型</option>';

      (models || []).forEach((model) => {
        const option = document.createElement("option");

        option.value = model.requested_model;
        option.textContent = model.provider
          ? `${model.requested_model} · ${model.provider}`
          : model.requested_model;

        modelFilter.appendChild(option);
      });

      if (
        Array.from(modelFilter.options).some(
          (option) => option.value === selectedValue
        )
      ) {
        modelFilter.value = selectedValue;
      }
    }


    function renderSummary(summary) {
      summaryTotalCalls.textContent =
        formatNumber(summary.total_calls);

      summarySuccessCalls.textContent =
        formatNumber(summary.success_calls);

      summaryFailedCalls.textContent =
        formatNumber(summary.failed_calls);

      summaryTotalTokens.textContent =
        formatNumber(summary.total_tokens);

      summaryTokenSplit.textContent =
        `${formatNumber(summary.input_tokens)} / ` +
        `${formatNumber(summary.output_tokens)}`;

      summaryAverageLatency.textContent =
        summary.average_latency_seconds === null
          ? "—"
          : formatLatency(
              summary.average_latency_seconds
            );

      populateModelFilter(summary.models);
    }


    function createTextCell(text) {
      const cell = document.createElement("td");
      cell.textContent = text;
      return cell;
    }


    function renderCalls(data) {
      const items = Array.isArray(data.items)
        ? data.items
        : [];

      currentTotal = Number(data.total || 0);
      tableBody.innerHTML = "";

      items.forEach((item) => {
        const row = document.createElement("tr");

        row.appendChild(
          createTextCell(formatDate(item.created_at))
        );

        const modelCell = document.createElement("td");
        const modelStrong = document.createElement("strong");
        const modelMeta = document.createElement("span");

        modelStrong.textContent = item.requested_model;
        modelMeta.textContent = [
          item.provider,
          item.actual_model
        ].filter(Boolean).join(" · ") || "—";

        modelCell.appendChild(modelStrong);
        modelCell.appendChild(modelMeta);
        row.appendChild(modelCell);

        const statusCell = document.createElement("td");
        const statusBadge = document.createElement("span");

        statusBadge.className =
          `usage-status ${item.status}`;
        statusBadge.textContent =
          item.status === "success"
            ? "成功"
            : "失败";

        statusCell.appendChild(statusBadge);
        row.appendChild(statusCell);

        row.appendChild(
          createTextCell(item.mode || "—")
        );

        row.appendChild(
          createTextCell(
            `${formatNumber(item.total_tokens)} ` +
            `(${formatNumber(item.input_tokens)} / ` +
            `${formatNumber(item.output_tokens)})`
          )
        );

        row.appendChild(
          createTextCell(
            formatLatency(item.total_latency_seconds)
          )
        );

        row.appendChild(
          createTextCell(
            formatNumber(item.message_count)
          )
        );

        const errorText = [
          item.error_type,
          item.error_message
        ].filter(Boolean).join(": ") || "—";

        const errorCell = createTextCell(errorText);
        errorCell.className = "usage-error-cell";
        errorCell.title = errorText;
        row.appendChild(errorCell);

        tableBody.appendChild(row);
      });

      emptyMessage.hidden = items.length !== 0;

      const pageNumber =
        Math.floor(currentOffset / USAGE_PAGE_SIZE) + 1;

      const pageCount = Math.max(
        1,
        Math.ceil(currentTotal / USAGE_PAGE_SIZE)
      );

      pageLabel.textContent =
        `第 ${pageNumber} / ${pageCount} 页`;

      resultCount.textContent =
        `共 ${formatNumber(currentTotal)} 条记录`;

      previousButton.disabled =
        loading || currentOffset === 0;

      nextButton.disabled =
        loading || !data.has_more;
    }


    function buildCallsPath() {
      const parameters = new URLSearchParams({
        limit: String(USAGE_PAGE_SIZE),
        offset: String(currentOffset)
      });

      if (statusFilter.value) {
        parameters.set("status", statusFilter.value);
      }

      if (modelFilter.value) {
        parameters.set(
          "requested_model",
          modelFilter.value
        );
      }

      return `/model-calls?${parameters.toString()}`;
    }


    async function loadCurrentUser() {
      const user = await authenticatedFetch("/auth/me");

      userName.textContent =
        user.display_name || user.email;
    }


    async function loadDashboard() {
      if (loading) {
        return;
      }

      setLoading(true);
      hideError();

      try {
        const [summary, calls] = await Promise.all([
          authenticatedFetch("/model-calls/summary"),
          authenticatedFetch(buildCallsPath())
        ]);

        renderSummary(summary);
        renderCalls(calls);
      }
      catch (error) {
        console.error(
          "Usage dashboard loading failed:",
          error
        );

        showError(`加载失败：${error.message}`);
      }
      finally {
        setLoading(false);

        previousButton.disabled =
          currentOffset === 0;

        nextButton.disabled =
          currentOffset + USAGE_PAGE_SIZE
          >= currentTotal;
      }
    }


    logoutButton.addEventListener(
      "click",
      () => {
        UnifiedLlmAuth.clearAuthentication();
        UnifiedLlmAuth.redirectToLogin();
      }
    );

    refreshButton.addEventListener(
      "click",
      loadDashboard
    );

    statusFilter.addEventListener(
      "change",
      () => {
        currentOffset = 0;
        loadDashboard();
      }
    );

    modelFilter.addEventListener(
      "change",
      () => {
        currentOffset = 0;
        loadDashboard();
      }
    );

    previousButton.addEventListener(
      "click",
      () => {
        currentOffset = Math.max(
          0,
          currentOffset - USAGE_PAGE_SIZE
        );
        loadDashboard();
      }
    );

    nextButton.addEventListener(
      "click",
      () => {
        if (
          currentOffset + USAGE_PAGE_SIZE
          < currentTotal
        ) {
          currentOffset += USAGE_PAGE_SIZE;
          loadDashboard();
        }
      }
    );


    async function startUsageDashboard() {
      try {
        await loadCurrentUser();
        await loadDashboard();
      }
      catch (error) {
        console.error(
          "Usage dashboard initialization failed:",
          error
        );

        showError(`初始化失败：${error.message}`);
      }
    }


    startUsageDashboard();
  }
);
