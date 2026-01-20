document.addEventListener('DOMContentLoaded', () => {
    if (!window.Auth || !window.APP_CONFIG) return;
    window.Auth.initNav();

    const form = document.getElementById('login-form');
    const errorBox = document.getElementById('form-error');

    if (!form) return;

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (errorBox) errorBox.textContent = '';

        const username = form.querySelector('input[name="username"]').value.trim();
        const password = form.querySelector('input[name="password"]').value.trim();
        if (!username || !password) {
            if (errorBox) errorBox.textContent = 'Please enter username and password.';
            return;
        }

        try {
            const response = await window.Auth.apiFetch('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Login failed');
            }
            window.Auth.setToken(data.access_token);
            window.Auth.setUser(data.user);
            if (data.user && data.user.username === 'admin') {
                window.location.href = 'admin.html';
            } else {
                window.location.href = 'index.html';
            }
        } catch (error) {
            if (errorBox) errorBox.textContent = error.message;
        }
    });
});
