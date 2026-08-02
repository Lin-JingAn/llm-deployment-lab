"use strict";


const API_BASE_URL = "http://127.0.0.1:8002";

const ACCESS_TOKEN_KEY = "unifiedLlmAccessToken";
const CURRENT_USER_KEY = "unifiedLlmCurrentUser";


function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}


function getStoredUser() {
  const rawUser = localStorage.getItem(
    CURRENT_USER_KEY
  );

  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser);
  }
  catch {
    localStorage.removeItem(CURRENT_USER_KEY);
    return null;
  }
}


function saveAuthentication(
  accessToken,
  user
) {
  localStorage.setItem(
    ACCESS_TOKEN_KEY,
    accessToken
  );

  localStorage.setItem(
    CURRENT_USER_KEY,
    JSON.stringify(user)
  );
}


function clearAuthentication() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(CURRENT_USER_KEY);
}


function redirectToLogin() {
  window.location.href = "login.html";
}


function redirectToHome() {
  window.location.href = "index.html";
}


function formatApiError(data, fallbackMessage) {
  if (
    data &&
    typeof data === "object" &&
    data.detail
  ) {
    if (
      typeof data.detail === "object" &&
      data.detail.message
    ) {
      return data.detail.message;
    }

    if (typeof data.detail === "string") {
      return data.detail;
    }
  }

  return fallbackMessage;
}


async function readResponseData(response) {
  const contentType =
    response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return await response.json();
  }

  return {
    detail: await response.text()
  };
}


async function registerUser({
  email,
  password,
  displayName
}) {
  const response = await fetch(
    `${API_BASE_URL}/auth/register`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        email,
        password,
        display_name: displayName || null
      })
    }
  );

  const data = await readResponseData(response);

  if (!response.ok) {
    throw new Error(
      formatApiError(
        data,
        "注册失败，请稍后重试。"
      )
    );
  }

  return data;
}


async function loginUser({
  email,
  password
}) {
  const response = await fetch(
    `${API_BASE_URL}/auth/login`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        email,
        password
      })
    }
  );

  const data = await readResponseData(response);

  if (!response.ok) {
    throw new Error(
      formatApiError(
        data,
        "登录失败，请检查邮箱和密码。"
      )
    );
  }

  saveAuthentication(
    data.access_token,
    data.user
  );

  return data;
}


async function fetchCurrentUser() {
  const accessToken = getAccessToken();

  if (!accessToken) {
    return null;
  }

  const response = await fetch(
    `${API_BASE_URL}/auth/me`,
    {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${accessToken}`
      }
    }
  );

  if (response.status === 401) {
    clearAuthentication();
    return null;
  }

  const data = await readResponseData(response);

  if (!response.ok) {
    throw new Error(
      formatApiError(
        data,
        "无法读取当前用户信息。"
      )
    );
  }

  localStorage.setItem(
    CURRENT_USER_KEY,
    JSON.stringify(data)
  );

  return data;
}


function logoutUser() {
  clearAuthentication();
  redirectToLogin();
}


window.UnifiedLlmAuth = {
  getAccessToken,
  getStoredUser,
  saveAuthentication,
  clearAuthentication,
  registerUser,
  loginUser,
  fetchCurrentUser,
  logoutUser,
  redirectToLogin,
  redirectToHome
};