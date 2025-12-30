document.addEventListener('DOMContentLoaded', () => {
    if (!window.ChatPage || !window.ChatPage.initChatPage) {
        console.error('ChatPage missing');
        return;
    }

    const apiBase = window.APP_CONFIG ? window.APP_CONFIG.API_BASE_URL : '';
    window.ChatPage.initChatPage({
        agent: 'competition',
        endpoint: `${apiBase}/api/agents/competition/chat`,
        greeting: 'Hello! I can help with competition strategies and practice.',
        storageKey: 'competition_conversation_id',
    });
});
