(() => {
    const meta = document.querySelector('meta[name="api-base"]');
    const apiBase = meta && meta.content ? meta.content : 'http://localhost:8000';
    window.APP_CONFIG = { API_BASE_URL: apiBase };
})();
