document.addEventListener('DOMContentLoaded', () => {
    if (!window.ChatPage || !window.ChatPage.initChatPage) {
        console.error('ChatPage missing');
        return;
    }

    const apiBase = window.APP_CONFIG ? window.APP_CONFIG.API_BASE_URL : '';
    window.ChatPage.initChatPage({
        agent: 'ideological',
        endpoint: `${apiBase}/api/agents/ideological/chat`,
        greeting: 'Hello! I can help with ideological guidance and discussion.',
        storageKey: 'ideological_conversation_id',
    });
});
