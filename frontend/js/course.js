document.addEventListener('DOMContentLoaded', () => {
    if (!window.ChatPage || !window.ChatPage.initChatPage) {
        console.error('ChatPage missing');
        return;
    }

    const apiBase = window.APP_CONFIG ? window.APP_CONFIG.API_BASE_URL : '';
    window.ChatPage.initChatPage({
        agent: 'course',
        endpoint: `${apiBase}/api/agents/course/chat`,
        greeting: 'Hello! I am the course assistant. Ask me about course topics.',
        storageKey: 'course_conversation_id',
    });
});
