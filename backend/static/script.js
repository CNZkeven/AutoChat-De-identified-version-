// 初始化聊天功能
document.addEventListener('DOMContentLoaded', function() {
    const messageArea = document.querySelector('.message-area');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.querySelector('.send-btn');

    // 添加消息到聊天区域
    function addMessage(text, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'message user-message' : 'message assistant-message';
        messageDiv.textContent = text;
        
        messageArea.appendChild(messageDiv);
        messageArea.scrollTop = messageArea.scrollHeight;
    }

    // 处理发送消息
    function handleSend() {
        const text = messageInput.value.trim();
        if (text) {
            addMessage(text, true);
            messageInput.value = '';
            
            // 模拟AI回复
            setTimeout(() => {
                addMessage('这是智能体的回复内容，实际会替换为API返回的数据', false);
            }, 800);
        }
    }

    // 事件监听
    sendButton.addEventListener('click', handleSend);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSend();
        }
    });

    // 初始欢迎消息
    setTimeout(() => {
        addMessage('您好！我是智能体助手，请问有什么可以帮您？', false);
    }, 500);

    // 设置智能体标题
    const path = window.location.pathname.split('/').pop();
    const agentName = path.replace('.html', '');
    const agentTitles = {
        
        'course': '课程型智能体',
        'task': '任务型智能体',
       
    };
    
    if (agentTitles[agentName]) {
        document.title = agentTitles[agentName];
        const titleElement = document.querySelector('.agent-title');
        if (titleElement) {
            titleElement.textContent = agentTitles[agentName];
        }
    }
});

// 通用聊天功能实现文件
// 提供基础聊天界面功能
// 包括消息显示、发送逻辑和智能体类型识别
