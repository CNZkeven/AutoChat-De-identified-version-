document.addEventListener('DOMContentLoaded', () => {
    if (!window.ChatPage || !window.ChatPage.initChatPage) {
        console.error('ChatPage missing');
        return;
    }

    const apiBase = window.APP_CONFIG ? window.APP_CONFIG.API_BASE_URL : '';
    window.ChatPage.initChatPage({
        agent: 'exploration',
        endpoint: `${apiBase}/api/agents/exploration/chat`,
        greeting: 'Hello! I can help with exploration and research questions.',
        storageKey: 'exploration_conversation_id',
    });
});
