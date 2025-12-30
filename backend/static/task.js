// 任务智能体会话初始化
document.addEventListener('DOMContentLoaded', () => {
    if (!window.ChatPage || !window.ChatPage.initChatPage) {
        console.error('ChatPage 未加载');
        return;
    }

    window.ChatPage.initChatPage({
        endpoint: '/task',
        greeting: '您好！我是任务学习助手，可以为您解答船舶与海洋工程相关的任务问题。',
        storageKey: 'task_conversation_id',
        agent: 'task',
    });
});
