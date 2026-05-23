window.onload = function () {

    console.log("JS RUNNING 🔥");

    // LOGIN
    const loginPassword = document.getElementById("password");
    const loginToggle = document.getElementById("togglePassword");

    if (loginPassword && loginToggle) {
        loginToggle.onclick = function () {
            const isPassword = loginPassword.type === "password";
            loginPassword.type = isPassword ? "text" : "password";
            loginToggle.textContent = isPassword ? "Hide" : "Show";
        };
    }

    // REGISTER
    const regPassword = document.getElementById("regPassword");
    const regToggle = document.getElementById("toggleRegPassword");

    if (regPassword && regToggle) {
        regToggle.onclick = function () {
            const isPassword = regPassword.type === "password";
            regPassword.type = isPassword ? "text" : "password";
            regToggle.textContent = isPassword ? "Hide" : "Show";
        };
    }
};

    