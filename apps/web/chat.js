"use strict";

const MODEL_API_BASE_URL = "http://127.0.0.1:8002";
const MAX_CONVERSATION_MESSAGES = 20;
const ACTIVE_CONVERSATION_KEY =
  "unifiedLlmActiveConversationId";


function initializeModelChat() {
  const chatForm =
    document.getElementById("chat-form");

  const chatInput =
    document.getElementById("chat-input");

  const modelSelect =
    document.getElementById("model-select");

  const tokenSelect =
    document.getElementById("max-new-tokens");

  const sendButton =
    document.getElementById("send-message-button");

  const apiStatus =
    document.getElementById("api-status");

  const chatMessages =
    document.getElementById("chat-messages");

  const conversationList =
    document.getElementById("conversation-list");

  const conversationEmpty =
    document.getElementById("conversation-empty");

  const newConversationButton =
    document.getElementById("new-conversation-button");

  const deleteConversationButton =
    document.getElementById("delete-conversation-button");

  const metricDevice =
    document.getElementById("metric-device");

  const metricTime =
    document.getElementById("metric-time");

  const metricInputTokens =
    document.getElementById("metric-input-tokens");

  const metricOutputTokens =
    document.getElementById("metric-output-tokens");

  const metricTotalTokens =
    document.getElementById("metric-memory");

  if (
    !chatForm ||
    !chatInput ||
    !modelSelect ||
    !sendButton ||
    !apiStatus ||
    !chatMessages ||
    !conversationList ||
    !conversationEmpty ||
    !newConversationButton ||
    !deleteConversationButton
  ) {
    console.error(
      "The page is missing required chat elements."
    );

    return;
  }

  let activeModelId = "";
  let activeModelDisplayName = "Model";
  let activeModelName = "Model";
  let activeProviderName = "Provider";

  let conversationMessages = [];
  let currentConversationId =
    localStorage.getItem(
      ACTIVE_CONVERSATION_KEY
    );

  let cachedConversations = [];


  function setApiStatus(status, text) {
    apiStatus.className =
      `api-status ${status}`;

    apiStatus.textContent = text;
  }


  function getAssistantRoleLabel() {
    return (
      activeModelDisplayName ||
      activeModelName ||
      "MODEL"
    ).toUpperCase();
  }


  function addMessage(
    role,
    text,
    extraClass = ""
  ) {
    const messageElement =
      document.createElement("div");

    const roleClass =
      role === "user"
        ? "user-message"
        : "assistant-message";

    messageElement.className =
      `chat-message ${roleClass} ${extraClass}`.trim();

    const roleElement =
      document.createElement("div");

    roleElement.className = "message-role";

    roleElement.textContent =
      role === "user"
        ? "YOU"
        : getAssistantRoleLabel();

    const textElement =
      document.createElement("p");

    textElement.textContent = text;

    messageElement.appendChild(roleElement);
    messageElement.appendChild(textElement);

    chatMessages.appendChild(messageElement);

    chatMessages.scrollTop =
      chatMessages.scrollHeight;

    return messageElement;
  }


  function trimConversationMessages(messages) {
    const trimmedMessages = messages.slice(
      -MAX_CONVERSATION_MESSAGES
    );

    while (
      trimmedMessages.length > 0 &&
      trimmedMessages[0].role === "assistant"
    ) {
      trimmedMessages.shift();
    }

    return trimmedMessages;
  }


  function resetMetrics() {
    if (metricDevice) {
      metricDevice.textContent =
        `${activeProviderName} · ` +
        `${activeModelDisplayName}`;
    }

    if (metricTime) {
      metricTime.textContent = "—";
    }

    if (metricInputTokens) {
      metricInputTokens.textContent = "—";
    }

    if (metricOutputTokens) {
      metricOutputTokens.textContent = "—";
    }

    if (metricTotalTokens) {
      metricTotalTokens.textContent =
        "等待请求";
    }
  }


  function updateMetrics(data) {
    const usage = data.usage || {};

    if (metricDevice) {
      const provider =
        data.provider || activeProviderName;

      const model =
        data.actual_model ||
        data.model ||
        data.display_name ||
        activeModelName;

      metricDevice.textContent =
        `${provider} · ${model}`;
    }

    if (metricTime) {
      const elapsedTime = Number(
        data.total_latency_seconds ||
        data.elapsed_time ||
        0
      );

      metricTime.textContent =
        `${elapsedTime.toFixed(2)} 秒`;
    }

    if (metricInputTokens) {
      metricInputTokens.textContent =
        usage.input_tokens ??
        data.input_tokens ??
        "—";
    }

    if (metricOutputTokens) {
      metricOutputTokens.textContent =
        usage.output_tokens ??
        data.output_tokens ??
        "—";
    }

    if (metricTotalTokens) {
      const totalTokens =
        usage.total_tokens ??
        data.total_tokens;

      metricTotalTokens.textContent =
        totalTokens !== undefined
          ? `${totalTokens} Token`
          : "—";
    }
  }


  function updateActiveModel(option) {
    if (!option) {
      return;
    }

    activeModelId = option.value;

    activeModelDisplayName =
      option.dataset.displayName ||
      option.textContent.trim() ||
      activeModelId;

    activeProviderName =
      option.dataset.provider ||
      activeProviderName;
  }


  function renderWelcomeMessage() {
    chatMessages.innerHTML = "";

    addMessage(
      "assistant",
      `当前模型：${activeModelDisplayName}。` +
        "你可以开始一个新的多轮对话。"
    );
  }


  function markActiveConversation() {
    const buttons = conversationList.querySelectorAll(
      "[data-conversation-id]"
    );

    buttons.forEach((button) => {
      button.classList.toggle(
        "active",
        button.dataset.conversationId ===
          currentConversationId
      );
    });

    deleteConversationButton.disabled =
      !currentConversationId;
  }


  function startNewConversation() {
    currentConversationId = null;
    conversationMessages = [];

    localStorage.removeItem(
      ACTIVE_CONVERSATION_KEY
    );

    renderWelcomeMessage();
    resetMetrics();
    markActiveConversation();
    chatInput.focus();
  }


  async function readResponseData(response) {
    const responseText =
      await response.text();

    if (!responseText) {
      return {};
    }

    try {
      return JSON.parse(responseText);
    }
    catch {
      return {
        detail: responseText
      };
    }
  }


  function getErrorMessage(
    data,
    fallbackMessage
  ) {
    if (!data) {
      return fallbackMessage;
    }

    if (typeof data.detail === "string") {
      return data.detail;
    }

    if (
      data.detail &&
      typeof data.detail === "object"
    ) {
      if (
        typeof data.detail.message === "string"
      ) {
        return data.detail.message;
      }

      return JSON.stringify(data.detail);
    }

    if (typeof data.message === "string") {
      return data.message;
    }

    return fallbackMessage;
  }


  async function authenticatedRequest(
    path,
    options = {}
  ) {
    const accessToken =
      UnifiedLlmAuth.getAccessToken();

    if (!accessToken) {
      UnifiedLlmAuth.redirectToLogin();

      throw new Error(
        "请先登录后再使用会话功能。"
      );
    }

    const response = await fetch(
      `${MODEL_API_BASE_URL}${path}`,
      {
        ...options,
        headers: {
          ...(options.headers || {}),
          "Authorization":
            `Bearer ${accessToken}`
        }
      }
    );

    const data =
      await readResponseData(response);

    if (response.status === 401) {
      UnifiedLlmAuth.clearAuthentication();
      UnifiedLlmAuth.redirectToLogin();

      throw new Error(
        "登录状态已失效，请重新登录。"
      );
    }

    if (!response.ok) {
      throw new Error(
        getErrorMessage(
          data,
          `HTTP ${response.status}`
        )
      );
    }

    return data;
  }


  function formatConversationTime(value) {
    if (!value) {
      return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "";
    }

    return date.toLocaleString(
      "zh-CN",
      {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      }
    );
  }


  function renderConversationList(conversations) {
    cachedConversations = conversations;
    conversationList.innerHTML = "";

    conversationEmpty.hidden =
      conversations.length > 0;

    conversations.forEach((conversation) => {
      const button =
        document.createElement("button");

      button.type = "button";
      button.className =
        "conversation-list-item";

      button.dataset.conversationId =
        conversation.id;

      const title =
        document.createElement("strong");

      title.textContent =
        conversation.title ||
        "新会话";

      const meta =
        document.createElement("span");

      const modelText =
        conversation.model_id ||
        "未选择模型";

      const timeText =
        formatConversationTime(
          conversation.updated_at
        );

      meta.textContent = timeText
        ? `${modelText} · ${timeText}`
        : modelText;

      button.appendChild(title);
      button.appendChild(meta);

      conversationList.appendChild(button);
    });

    markActiveConversation();
  }


  async function loadConversationList({
    restore = false
  } = {}) {
    const conversations =
      await authenticatedRequest(
        "/conversations",
        {
          method: "GET",
          cache: "no-store"
        }
      );

    renderConversationList(
      Array.isArray(conversations)
        ? conversations
        : []
    );

    if (!restore) {
      return;
    }

    let conversationToRestore = null;

    if (currentConversationId) {
      conversationToRestore =
        cachedConversations.find(
          (conversation) =>
            conversation.id ===
            currentConversationId
        );
    }

    if (
      !conversationToRestore &&
      cachedConversations.length > 0
    ) {
      conversationToRestore =
        cachedConversations[0];
    }

    if (conversationToRestore) {
      await loadConversation(
        conversationToRestore.id
      );
    }
    else {
      startNewConversation();
    }
  }


  async function loadConversation(
    conversationId
  ) {
    setApiStatus(
      "checking",
      "正在加载历史会话"
    );

    const conversation =
      await authenticatedRequest(
        `/conversations/${conversationId}`,
        {
          method: "GET",
          cache: "no-store"
        }
      );

    currentConversationId =
      conversation.id;

    localStorage.setItem(
      ACTIVE_CONVERSATION_KEY,
      currentConversationId
    );

    if (conversation.model_id) {
      const matchingOption = Array
        .from(modelSelect.options)
        .find(
          (option) =>
            option.value ===
            conversation.model_id
        );

      if (matchingOption) {
        modelSelect.value =
          conversation.model_id;

        updateActiveModel(
          matchingOption
        );
      }
    }

    conversationMessages = (
      Array.isArray(conversation.messages)
        ? conversation.messages
        : []
    )
      .filter(
        (message) =>
          ["system", "user", "assistant"]
            .includes(message.role)
      )
      .map(
        (message) => ({
          role: message.role,
          content: message.content
        })
      );

    chatMessages.innerHTML = "";

    if (conversationMessages.length === 0) {
      renderWelcomeMessage();
    }
    else {
      conversationMessages.forEach(
        (message) => {
          addMessage(
            message.role,
            message.content
          );
        }
      );
    }

    resetMetrics();
    markActiveConversation();

    setApiStatus(
      "online",
      `已恢复会话 · ${activeModelDisplayName}`
    );

    chatInput.focus();
  }


  async function checkModelApi() {
    setApiStatus(
      "checking",
      "正在检查服务"
    );

    const response = await fetch(
      `${MODEL_API_BASE_URL}/health`,
      {
        method: "GET",
        cache: "no-store"
      }
    );

    const data =
      await readResponseData(response);

    if (!response.ok) {
      throw new Error(
        getErrorMessage(
          data,
          `HTTP ${response.status}`
        )
      );
    }

    if (data.status !== "healthy") {
      throw new Error(
        "FastAPI 服务尚未就绪。"
      );
    }

    setApiStatus(
      "online",
      "统一网关在线"
    );
  }


  async function loadAvailableModels() {
    modelSelect.disabled = true;
    modelSelect.innerHTML = "";

    const loadingOption =
      document.createElement("option");

    loadingOption.value = "";
    loadingOption.textContent =
      "正在加载模型";

    modelSelect.appendChild(
      loadingOption
    );

    const response = await fetch(
      `${MODEL_API_BASE_URL}/models`,
      {
        method: "GET",
        cache: "no-store"
      }
    );

    const data =
      await readResponseData(response);

    if (!response.ok) {
      throw new Error(
        getErrorMessage(
          data,
          `HTTP ${response.status}`
        )
      );
    }

    const availableModels =
      Array.isArray(data.models)
        ? data.models.filter(
            (model) => model.enabled
          )
        : [];

    if (availableModels.length === 0) {
      throw new Error(
        "后端没有返回可用模型。"
      );
    }

    modelSelect.innerHTML = "";

    availableModels.forEach((model) => {
      const option =
        document.createElement("option");

      option.value = model.id;

      option.textContent =
        `${model.display_name} · ` +
        `${model.provider}`;

      option.dataset.displayName =
        model.display_name;

      option.dataset.provider =
        model.provider;

      modelSelect.appendChild(option);
    });

    const defaultModelId =
      data.default_model ||
      availableModels[0].id;

    const defaultOption = Array
      .from(modelSelect.options)
      .find(
        (option) =>
          option.value === defaultModelId
      );

    if (defaultOption) {
      modelSelect.value =
        defaultModelId;
    }
    else {
      modelSelect.selectedIndex = 0;
    }

    updateActiveModel(
      modelSelect.selectedOptions[0]
    );

    modelSelect.disabled = false;
    resetMetrics();
  }


  modelSelect.addEventListener(
    "change",
    () => {
      updateActiveModel(
        modelSelect.selectedOptions[0]
      );

      activeModelName =
        activeModelDisplayName;

      setApiStatus(
        "online",
        `服务在线 · ${activeModelDisplayName}`
      );

      resetMetrics();
    }
  );


  conversationList.addEventListener(
    "click",
    async (event) => {
      const button = event.target.closest(
        "[data-conversation-id]"
      );

      if (!button) {
        return;
      }

      try {
        await loadConversation(
          button.dataset.conversationId
        );
      }
      catch (error) {
        console.error(
          "Conversation load failed:",
          error
        );

        setApiStatus(
          "offline",
          "会话加载失败"
        );

        alert(error.message);
      }
    }
  );


  newConversationButton.addEventListener(
    "click",
    () => {
      startNewConversation();

      setApiStatus(
        "online",
        `新会话 · ${activeModelDisplayName}`
      );
    }
  );


  deleteConversationButton.addEventListener(
    "click",
    async () => {
      if (!currentConversationId) {
        return;
      }

      const shouldDelete = confirm(
        "确定删除当前会话及其全部消息吗？"
      );

      if (!shouldDelete) {
        return;
      }

      try {
        await authenticatedRequest(
          `/conversations/${currentConversationId}`,
          {
            method: "DELETE"
          }
        );

        startNewConversation();

        await loadConversationList({
          restore: true
        });
      }
      catch (error) {
        console.error(
          "Conversation delete failed:",
          error
        );

        alert(error.message);
      }
    }
  );


  chatForm.addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();

      const message =
        chatInput.value.trim();

      const selectedModelId =
        modelSelect.value ||
        activeModelId;

      const maxTokens = Number(
        tokenSelect?.value || 256
      );

      if (!message) {
        return;
      }

      if (!selectedModelId) {
        alert(
          "当前没有可用模型，请检查后端模型列表。"
        );

        return;
      }

      const userMessage = {
        role: "user",
        content: message
      };

      const requestMessages =
        trimConversationMessages([
          ...conversationMessages,
          userMessage
        ]);

      addMessage("user", message);

      chatInput.value = "";
      sendButton.disabled = true;
      modelSelect.disabled = true;
      sendButton.textContent = "生成中";

      const loadingMessage = addMessage(
        "assistant",
        "正在生成回答……",
        "loading-message"
      );

      try {
        const responseData =
          await authenticatedRequest(
            "/chat",
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json"
              },
              body: JSON.stringify({
                conversation_id:
                  currentConversationId,
                model: selectedModelId,
                messages: requestMessages,
                max_tokens: maxTokens
              })
            }
          );

        if (!responseData.reply) {
          throw new Error(
            "模型没有返回回答内容。"
          );
        }

        currentConversationId =
          responseData.conversation_id ||
          currentConversationId;

        if (currentConversationId) {
          localStorage.setItem(
            ACTIVE_CONVERSATION_KEY,
            currentConversationId
          );
        }

        activeModelId =
          responseData.model_id ||
          selectedModelId;

        activeModelName =
          responseData.actual_model ||
          responseData.model ||
          activeModelName;

        activeModelDisplayName =
          responseData.display_name ||
          activeModelDisplayName;

        activeProviderName =
          responseData.provider ||
          activeProviderName;

        conversationMessages =
          trimConversationMessages([
            ...requestMessages,
            {
              role: "assistant",
              content: responseData.reply
            }
          ]);

        loadingMessage.remove();

        addMessage(
          "assistant",
          responseData.reply
        );

        updateMetrics(responseData);

        await loadConversationList();

        setApiStatus(
          "online",
          `服务在线 · ${activeModelDisplayName}`
        );
      }
      catch (error) {
        console.error(
          "Model request failed:",
          error
        );

        loadingMessage.remove();

        const errorMessage = addMessage(
          "assistant",
          `请求失败：${error.message}`
        );

        errorMessage.classList.add(
          "error-message"
        );

        setApiStatus(
          "offline",
          "请求失败"
        );

        try {
          await loadConversationList();
        }
        catch {
          // Keep the original model error visible.
        }
      }
      finally {
        sendButton.disabled = false;

        if (modelSelect.options.length > 0) {
          modelSelect.disabled = false;
        }

        sendButton.textContent =
          "发送问题";

        chatInput.focus();
      }
    }
  );


  async function startModelChat() {
    try {
      await checkModelApi();
      await loadAvailableModels();
      await loadConversationList({
        restore: true
      });
    }
    catch (error) {
      console.error(
        "Model chat initialization failed:",
        error
      );

      setApiStatus(
        "offline",
        "模型或会话加载失败"
      );

      chatMessages.innerHTML = "";

      addMessage(
        "assistant",
        `初始化失败：${error.message}`,
        "error-message"
      );
    }
  }


  startModelChat();
}


if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    initializeModelChat
  );
}
else {
  initializeModelChat();
}
