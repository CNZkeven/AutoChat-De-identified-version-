// 课程智能体会话初始化
document.addEventListener('DOMContentLoaded', () => {
    if (!window.ChatPage || !window.ChatPage.initChatPage) {
        console.error('ChatPage 未加载');
        return;
    }

    window.ChatPage.initChatPage({
        endpoint: '/course',
        greeting: '您好！我是课程学习助手，可以为您解答船舶与海洋工程相关的课程问题。',
        storageKey: 'course_conversation_id',
        agent: 'course',
    });
});
