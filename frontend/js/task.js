document.addEventListener('DOMContentLoaded', () => {
    if (!window.ChatPage || !window.ChatPage.initChatPage) {
        console.error('ChatPage missing');
        return;
    }

    const apiBase = window.APP_CONFIG ? window.APP_CONFIG.API_BASE_URL : '';
    window.ChatPage.initChatPage({
        agent: 'task',
        endpoint: `${apiBase}/api/agents/task/chat`,
        greeting: 'Hello! I can help with task planning and execution.',
        storageKey: 'task_conversation_id',
    });
});
