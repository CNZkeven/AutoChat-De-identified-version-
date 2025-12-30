document.addEventListener('DOMContentLoaded', () => {
    if (!window.Auth || !window.APP_CONFIG) return;
    window.Auth.initNav();

    const form = document.getElementById('register-form');
    const errorBox = document.getElementById('form-error');

    if (!form) return;

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (errorBox) errorBox.textContent = '';

        const username = form.querySelector('input[name="username"]').value.trim();
        const password = form.querySelector('input[name="password"]').value.trim();
        const confirm = form.querySelector('input[name="confirm"]').value.trim();

        if (!username || !password) {
            if (errorBox) errorBox.textContent = 'Please enter username and password.';
            return;
        }
        if (password !== confirm) {
            if (errorBox) errorBox.textContent = 'Passwords do not match.';
            return;
        }

        try {
            const response = await window.Auth.apiFetch('/api/auth/register', {
                method: 'POST',
                body: JSON.stringify({ username, password }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Registration failed');
            }
            window.Auth.setToken(data.access_token);
            window.Auth.setUser(data.user);
            window.location.href = 'index.html';
        } catch (error) {
            if (errorBox) errorBox.textContent = error.message;
        }
    });
});
