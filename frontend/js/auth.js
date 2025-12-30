(() => {
    const TOKEN_KEY = 'auth_token';
    const USER_KEY = 'auth_user';

    function getToken() {
        return window.localStorage.getItem(TOKEN_KEY);
    }

    function setToken(token) {
        window.localStorage.setItem(TOKEN_KEY, token);
    }

    function clearToken() {
        window.localStorage.removeItem(TOKEN_KEY);
    }

    function getUser() {
        const raw = window.localStorage.getItem(USER_KEY);
        if (!raw) return null;
        try {
            return JSON.parse(raw);
        } catch (error) {
            return null;
        }
    }

    function setUser(user) {
        window.localStorage.setItem(USER_KEY, JSON.stringify(user));
    }

    function clearUser() {
        window.localStorage.removeItem(USER_KEY);
    }

    function clearAuth() {
        clearToken();
        clearUser();
    }

    function requireAuth() {
        if (!getToken()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }

    function authHeaders() {
        const token = getToken();
        return token ? { Authorization: `Bearer ${token}` } : {};
    }

    async function apiFetch(path, options = {}) {
        const base = window.APP_CONFIG ? window.APP_CONFIG.API_BASE_URL : '';
        const url = path.startsWith('http') ? path : `${base}${path}`;
        const headers = {
            'Content-Type': 'application/json',
            ...authHeaders(),
            ...(options.headers || {}),
        };
        const response = await fetch(url, { ...options, headers });
        if (response.status === 401) {
            clearAuth();
            if (!path.includes('/api/auth/')) {
                window.location.href = 'login.html';
            }
        }
        return response;
    }

    function initNav() {
        const user = getUser();
        const userEl = document.getElementById('nav-user');
        const loginEl = document.getElementById('nav-login');
        const registerEl = document.getElementById('nav-register');
        const logoutEl = document.getElementById('nav-logout');

        if (userEl) {
            userEl.textContent = user ? `Hello, ${user.username}` : '';
            userEl.style.display = user ? 'inline-flex' : 'none';
        }
        if (loginEl) loginEl.style.display = user ? 'none' : 'inline-flex';
        if (registerEl) registerEl.style.display = user ? 'none' : 'inline-flex';
        if (logoutEl) {
            logoutEl.style.display = user ? 'inline-flex' : 'none';
            logoutEl.addEventListener('click', (event) => {
                event.preventDefault();
                clearAuth();
                window.location.href = 'login.html';
            });
        }
    }

    window.Auth = {
        getToken,
        setToken,
        getUser,
        setUser,
        clearAuth,
        requireAuth,
        authHeaders,
        apiFetch,
        initNav,
    };
})();
