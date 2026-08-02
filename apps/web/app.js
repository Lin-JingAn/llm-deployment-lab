// ========================================
// 获取网页中的元素
// ========================================

const logForm = document.getElementById("log-form");
const logDateInput = document.getElementById("log-date");
const logStageInput = document.getElementById("log-stage");
const logCompletedInput = document.getElementById("log-completed");
const logCommandsInput = document.getElementById("log-commands");
const logProblemInput = document.getElementById("log-problem");
const logSolutionInput = document.getElementById("log-solution");
const logNextStepInput = document.getElementById("log-next-step");

const logList = document.getElementById("log-list");
const emptyMessage = document.getElementById("empty-message");
const clearAllButton = document.getElementById("clear-all-button");
const currentStage = document.getElementById("current-stage");


// ========================================
// 浏览器本地存储名称
// ========================================

const STORAGE_KEY = "llmDeploymentLogs";


// ========================================
// 当前正在编辑的记录编号
// null 表示正在添加新记录
// ========================================

let editingLogId = null;


// ========================================
// 获取今天的日期
// 格式：2026-07-28
// ========================================

function getTodayDate() {
  const today = new Date();

  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}


// ========================================
// 从浏览器中读取记录
// ========================================

function getLogs() {
  const savedLogs = localStorage.getItem(STORAGE_KEY);

  if (!savedLogs) {
    return [];
  }

  try {
    return JSON.parse(savedLogs);
  } catch (error) {
    console.error("读取记录失败：", error);
    return [];
  }
}


// ========================================
// 将记录保存到浏览器
// ========================================

function saveLogs(logs) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(logs));
}


// ========================================
// 生成唯一编号
// ========================================

function createLogId() {
  if (window.crypto && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}


// ========================================
// 防止用户填写的内容被当成HTML代码
// ========================================

function escapeHtml(text = "") {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


// ========================================
// 将换行符转换成网页换行
// ========================================

function formatText(text = "") {
  return escapeHtml(text).replaceAll("\n", "<br>");
}


// ========================================
// 清空表单并恢复默认状态
// ========================================

function resetForm() {
  logForm.reset();

  logDateInput.value = getTodayDate();
  editingLogId = null;

  const submitButton =
    logForm.querySelector('button[type="submit"]');

  submitButton.textContent = "保存记录";
}


// ========================================
// 更新首页的当前阶段
// ========================================

function updateCurrentStage(logs) {
  if (logs.length === 0) {
    currentStage.textContent =
      "已完成服务器环境检查，准备创建独立Conda环境。";

    return;
  }

  const sortedLogs = [...logs].sort(
    (firstLog, secondLog) => {
      if (firstLog.date === secondLog.date) {
        return secondLog.createdAt - firstLog.createdAt;
      }

      return secondLog.date.localeCompare(firstLog.date);
    }
  );

  currentStage.textContent = sortedLogs[0].stage;
}


// ========================================
// 将历史记录显示到网页中
// ========================================

function renderLogs() {
  const logs = getLogs();

  const sortedLogs = [...logs].sort(
    (firstLog, secondLog) => {
      if (firstLog.date === secondLog.date) {
        return secondLog.createdAt - firstLog.createdAt;
      }

      return secondLog.date.localeCompare(firstLog.date);
    }
  );

  logList.innerHTML = "";

  if (sortedLogs.length === 0) {
    emptyMessage.style.display = "block";
  } else {
    emptyMessage.style.display = "none";
  }

  sortedLogs.forEach((log) => {
    const logCard = document.createElement("article");

    logCard.className = "log-card";

    logCard.innerHTML = `
      <div class="log-card-header">
        <div>
          <div class="log-date">
            ${escapeHtml(log.date)}
          </div>

          <h4>
            ${escapeHtml(log.stage)}
          </h4>
        </div>

        <div class="log-actions">
          <button
            class="small-button"
            type="button"
            data-action="edit"
            data-id="${log.id}"
          >
            编辑
          </button>

          <button
            class="small-button delete-button"
            type="button"
            data-action="delete"
            data-id="${log.id}"
          >
            删除
          </button>
        </div>
      </div>

      <div class="log-details">

        <div class="log-detail full-width">
          <h5>今日完成</h5>
          <p>${formatText(log.completed)}</p>
        </div>

        <div class="log-detail full-width">
          <h5>执行命令</h5>
          <pre>${escapeHtml(log.commands || "无")}</pre>
        </div>

        <div class="log-detail">
          <h5>遇到的问题</h5>
          <p>${formatText(log.problem || "无")}</p>
        </div>

        <div class="log-detail">
          <h5>解决方法</h5>
          <p>${formatText(log.solution || "待补充")}</p>
        </div>

        <div class="log-detail full-width">
          <h5>下一步计划</h5>
          <p>${formatText(log.nextStep || "待安排")}</p>
        </div>

      </div>
    `;

    logList.appendChild(logCard);
  });

  updateCurrentStage(logs);
}


// ========================================
// 保存表单中的记录
// ========================================

logForm.addEventListener("submit", function (event) {
  event.preventDefault();

  const stage = logStageInput.value.trim();
  const completed = logCompletedInput.value.trim();

  if (!stage || !completed) {
    alert("请填写“当前阶段”和“今日完成”。");
    return;
  }

  const logs = getLogs();

  const logData = {
    id: editingLogId || createLogId(),
    date: logDateInput.value,
    stage: stage,
    completed: completed,
    commands: logCommandsInput.value.trim(),
    problem: logProblemInput.value.trim(),
    solution: logSolutionInput.value.trim(),
    nextStep: logNextStepInput.value.trim(),
    createdAt: Date.now()
  };

  if (editingLogId) {
    const logIndex = logs.findIndex(
      (log) => log.id === editingLogId
    );

    if (logIndex !== -1) {
      logData.createdAt = logs[logIndex].createdAt;
      logs[logIndex] = logData;
    }
  } else {
    logs.push(logData);
  }

  saveLogs(logs);
  renderLogs();
  resetForm();

  alert("记录保存成功。");
});


// ========================================
// 编辑或删除记录
// ========================================

logList.addEventListener("click", function (event) {
  const clickedButton = event.target.closest("button");

  if (!clickedButton) {
    return;
  }

  const action = clickedButton.dataset.action;
  const logId = clickedButton.dataset.id;

  if (!action || !logId) {
    return;
  }

  const logs = getLogs();

  if (action === "edit") {
    const selectedLog = logs.find(
      (log) => log.id === logId
    );

    if (!selectedLog) {
      return;
    }

    logDateInput.value = selectedLog.date;
    logStageInput.value = selectedLog.stage;
    logCompletedInput.value = selectedLog.completed;
    logCommandsInput.value = selectedLog.commands;
    logProblemInput.value = selectedLog.problem;
    logSolutionInput.value = selectedLog.solution;
    logNextStepInput.value = selectedLog.nextStep;

    editingLogId = selectedLog.id;

    const submitButton =
      logForm.querySelector('button[type="submit"]');

    submitButton.textContent = "更新记录";

    document
      .getElementById("daily-log")
      .scrollIntoView({
        behavior: "smooth"
      });
  }

  if (action === "delete") {
    const shouldDelete = confirm(
      "确定要删除这条记录吗？"
    );

    if (!shouldDelete) {
      return;
    }

    const updatedLogs = logs.filter(
      (log) => log.id !== logId
    );

    saveLogs(updatedLogs);
    renderLogs();

    if (editingLogId === logId) {
      resetForm();
    }
  }
});


// ========================================
// 清空全部记录
// ========================================

clearAllButton.addEventListener("click", function () {
  const logs = getLogs();

  if (logs.length === 0) {
    alert("目前没有可以清空的记录。");
    return;
  }

  const shouldClear = confirm(
    "确定要清空全部记录吗？此操作无法恢复。"
  );

  if (!shouldClear) {
    return;
  }

  localStorage.removeItem(STORAGE_KEY);

  resetForm();
  renderLogs();
});


// ========================================
// 页面第一次打开时执行
// ========================================

logDateInput.value = getTodayDate();

renderLogs();


// ========================================
// 统一大模型网关多轮对话功能
