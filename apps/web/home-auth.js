"use strict";


document.addEventListener(
  "DOMContentLoaded",
  async () => {
    const guestActions =
      document.getElementById("guest-actions");

    const userActions =
      document.getElementById("user-actions");

    const currentUserName =
      document.getElementById("current-user-name");

    const logoutButton =
      document.getElementById("logout-button");


    function showGuestState() {
      guestActions.hidden = false;
      userActions.hidden = true;
      currentUserName.textContent = "";
    }


    function showUserState(user) {
      guestActions.hidden = true;
      userActions.hidden = false;

      currentUserName.textContent =
        user.display_name ||
        user.email ||
        "已登录用户";
    }


    showGuestState();


    try {
      const currentUser =
        await UnifiedLlmAuth.fetchCurrentUser();

      if (currentUser) {
        showUserState(currentUser);
      }
    }
    catch (error) {
      console.error(
        "读取用户登录状态失败：",
        error
      );

      showGuestState();
    }


    logoutButton.addEventListener(
      "click",
      () => {
        UnifiedLlmAuth.logoutUser();
      }
    );
  }
);