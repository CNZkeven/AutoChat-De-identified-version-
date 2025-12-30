document.addEventListener('DOMContentLoaded', () => {
    if (!window.ChatPage || !window.ChatPage.initChatPage) {
        console.error('ChatPage missing');
        return;
    }

    const apiBase = window.APP_CONFIG ? window.APP_CONFIG.API_BASE_URL : '';
    window.ChatPage.initChatPage({
        agent: 'evaluation',
        endpoint: `${apiBase}/api/agents/evaluation/chat`,
        greeting: 'Hello! I can help with evaluations and feedback.',
        storageKey: 'evaluation_conversation_id',
    });
});
