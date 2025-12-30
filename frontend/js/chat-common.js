(() => {
    function initChatPage({
        agent,
        endpoint,
        greeting,
        chatContainerId = 'chat-container',
        inputId = 'message-input',
        buttonId = 'send-button',
        conversationListId = 'conversation-list',
        newConversationBtnId = 'new-conv-btn',
        statusId = 'conversation-status',
        selectToggleId = 'select-mode-toggle',
        useSelectedBtnId = 'use-selected-btn',
        storageKey = 'conversation_id',
        timeoutMs = 30000,
    } = {}) {
        if (!agent || !endpoint) {
            console.error('initChatPage requires agent and endpoint');
            return;
        }

        if (!window.Auth || !window.APP_CONFIG) {
            console.error('Auth or APP_CONFIG missing');
            return;
        }

        if (!window.Auth.requireAuth()) {
            return;
        }

        window.Auth.initNav();

        const chatContainer = document.getElementById(chatContainerId);
        const messageInput = document.getElementById(inputId);
        const sendButton = document.getElementById(buttonId);
        const conversationList = document.getElementById(conversationListId);
        const newConvBtn = document.getElementById(newConversationBtnId);
        const statusBox = document.getElementById(statusId);
        const selectToggle = document.getElementById(selectToggleId);
        const useSelectedBtn = document.getElementById(useSelectedBtnId);

        if (!chatContainer || !messageInput || !sendButton || !conversationList || !newConvBtn) {
            console.error('initChatPage: missing chat DOM elements');
            return;
        }

        let isGenerating = false;
        let messageHistory = [];
        let messagesState = [];
        let selectedRange = null;
        let isSelectMode = false;
        let currentConversationId = null;
        let conversations = [];

        const apiBase = window.APP_CONFIG.API_BASE_URL;
        const conversationBase = `${apiBase}/api/conversations`;
        const agentParam = `agent=${encodeURIComponent(agent)}`;
        const listUrl = `${conversationBase}?${agentParam}`;
        const conversationUrl = (id) => `${conversationBase}/${id}?${agentParam}`;
        const messagesUrl = (id) => `${conversationBase}/${id}/messages?${agentParam}`;
        const selectionKey = (convId) => `${storageKey}_selected_range_${convId}`;

        newConvBtn.addEventListener('click', handleCreateConversation);
        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !isGenerating) sendMessage();
        });
        if (selectToggle) {
            selectToggle.addEventListener('change', (e) => {
                isSelectMode = e.target.checked;
                applySelectionHighlight();
            });
        }
        if (useSelectedBtn) {
            useSelectedBtn.addEventListener('click', handleUseSelectedPrompt);
        }

        bootstrap().catch((e) => {
            console.error(e);
            setStatus('Initialization failed', true);
        });

        async function bootstrap() {
            await loadConversations();
            const lastId = window.localStorage.getItem(storageKey);
            const initialId = conversations.find((c) => c.id === Number(lastId))?.id || conversations[0]?.id;
            if (initialId) {
                await selectConversation(initialId);
            }
        }

        function setStatus(text, isError = false) {
            if (!statusBox) return;
            statusBox.textContent = text || '';
            statusBox.classList.toggle('status-error', Boolean(isError));
        }

        async function loadConversations() {
            setStatus('Loading conversations...');
            const data = await fetchJson(listUrl);
            conversations = data || [];
            if (!conversations.length) {
                await handleCreateConversation();
                return;
            }
            renderConversationList();
            setStatus('');
        }

        function renderConversationList() {
            conversationList.innerHTML = '';
            conversations.forEach((conv) => {
                const item = document.createElement('div');
                item.className = 'conversation-item';
                if (conv.id === currentConversationId) item.classList.add('active');
                item.dataset.id = conv.id;
                const title = document.createElement('div');
                title.className = 'conversation-title';
                title.textContent = conv.title || 'Untitled';

                const meta = document.createElement('div');
                meta.className = 'conversation-meta';
                meta.textContent = conv.status === 'archived' ? 'Archived' : 'Active';

                const actions = document.createElement('div');
                actions.className = 'conversation-actions';
                const renameBtn = document.createElement('button');
                renameBtn.className = 'conv-btn';
                renameBtn.textContent = 'Rename';
                renameBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    handleRename(conv.id);
                });
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'conv-btn danger';
                deleteBtn.textContent = 'Delete';
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    handleDelete(conv.id);
                });
                actions.appendChild(renameBtn);
                actions.appendChild(deleteBtn);

                item.appendChild(title);
                item.appendChild(meta);
                item.appendChild(actions);
                item.addEventListener('click', () => selectConversation(conv.id));
                conversationList.appendChild(item);
            });
        }

        async function handleCreateConversation() {
            try {
                setStatus('Creating conversation...');
                const created = await fetchJson(listUrl, {
                    method: 'POST',
                    body: JSON.stringify({ title: 'New conversation' }),
                });
                conversations.unshift(created);
                renderConversationList();
                await selectConversation(created.id);
                setStatus('');
            } catch (e) {
                console.error(e);
                setStatus('Failed to create conversation', true);
            }
        }

        async function handleRename(id) {
            const name = window.prompt('Enter a new conversation title');
            if (name === null) return;
            const title = name.trim() || 'New conversation';
            try {
                const updated = await fetchJson(conversationUrl(id), {
                    method: 'PATCH',
                    body: JSON.stringify({ title }),
                });
                conversations = conversations.map((c) => (c.id === id ? updated : c));
                renderConversationList();
                if (id === currentConversationId) setStatus('Renamed');
            } catch (e) {
                console.error(e);
                setStatus('Failed to rename', true);
            }
        }

        async function handleDelete(id) {
            const ok = window.confirm('Delete this conversation?');
            if (!ok) return;
            try {
                await fetchJson(conversationUrl(id), { method: 'DELETE' });
                conversations = conversations.filter((c) => c.id !== id);
                if (!conversations.length) {
                    await handleCreateConversation();
                    return;
                }
                const fallbackId = conversations[0].id;
                await selectConversation(id === currentConversationId ? fallbackId : currentConversationId);
                renderConversationList();
                setStatus('Deleted');
            } catch (e) {
                console.error(e);
                setStatus('Failed to delete', true);
            }
        }

        async function selectConversation(id) {
            if (!id) return;
            currentConversationId = id;
            window.localStorage.setItem(storageKey, String(id));
            renderConversationList();
            await loadMessages(id);
        }

        async function loadMessages(id) {
            chatContainer.innerHTML = '';
            messageHistory = [];
            messagesState = [];
            selectedRange = null;
            applySelectionHighlight();
            setStatus('Loading messages...');
            try {
                const msgs = await fetchJson(messagesUrl(id));
                messagesState = (msgs || []).map((m) => ({
                    id: m.id,
                    role: m.role,
                    content: m.content,
                    createdAt: m.created_at,
                }));

                messagesState.forEach((m, idx) => {
                    renderMessageCard(m, idx);
                    messageHistory.push({ role: m.role, content: m.content });
                });

                if (!messagesState.length && greeting) {
                    renderGreeting(greeting);
                }

                restoreSelection();
                setStatus('');
            } catch (e) {
                console.error(e);
                setStatus('Failed to load messages', true);
            }
        }

        async function sendMessage() {
            const userMessage = messageInput.value.trim();
            if (!userMessage || isGenerating) return;
            if (!currentConversationId) {
                await handleCreateConversation();
            }
            appendMessage('user', userMessage);
            messageInput.value = '';
            const loadingId = showLoading();
            isGenerating = true;

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
            const selectedMessagesPayload = getSelectedMessages();

            try {
                const response = await window.Auth.apiFetch(endpoint, {
                    method: 'POST',
                    signal: controller.signal,
                    headers: { Accept: 'text/event-stream' },
                    body: JSON.stringify({
                        conversation_id: currentConversationId,
                        messages: messageHistory,
                        selected_messages: selectedMessagesPayload,
                    }),
                });

                clearTimeout(timeoutId);
                if (!response.ok) throw new Error(response.statusText);
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let aiResponse = '';
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk
                        .split('\n\n')
                        .filter((line) => line.startsWith('data: '));
                    for (const line of lines) {
                        try {
                            const data = JSON.parse(line.replace('data: ', ''));
                            if (data.error) {
                                throw new Error(data.error);
                            }
                            if (data.content) {
                                aiResponse += data.content;
                                updateMessage(loadingId, aiResponse);
                            }
                        } catch (e) {
                            if (e.message !== 'Unexpected end of JSON input') {
                                console.error('Parse error:', e);
                                throw e;
                            }
                        }
                    }
                }
                messageHistory.push({ role: 'assistant', content: aiResponse });
            } catch (error) {
                const isAbort = error.name === 'AbortError';
                showError(isAbort ? 'Request timed out' : 'Request failed');
                console.error('Request error:', error);
            } finally {
                clearTimeout(timeoutId);
                removeLoading(loadingId);
                isGenerating = false;
                if (currentConversationId) {
                    await loadMessages(currentConversationId);
                }
            }
        }

        async function fetchJson(url, options = {}) {
            const res = await window.Auth.apiFetch(url, options);
            let data;
            try {
                data = await res.json();
            } catch (e) {
                data = null;
            }
            if (!res.ok) {
                const msg = (data && (data.detail || data.error)) || res.statusText;
                throw new Error(msg || 'Request failed');
            }
            return data;
        }

        function renderMessageCard(message, seq) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message message-${message.role}`;
            messageDiv.dataset.index = seq;
            messageDiv.dataset.id = message.id || '';
            if (isSelectMode) messageDiv.classList.add('select-mode');
            messageDiv.addEventListener('click', () => handleSelect(seq));

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'message-select-checkbox';
            checkbox.addEventListener('click', (e) => {
                e.stopPropagation();
                handleSelect(seq);
            });

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = message.content;

            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = message.createdAt
                ? new Date(message.createdAt).toLocaleTimeString()
                : new Date().toLocaleTimeString();

            const bodyDiv = document.createElement('div');
            bodyDiv.className = 'message-body';
            bodyDiv.appendChild(contentDiv);
            bodyDiv.appendChild(timeDiv);

            messageDiv.appendChild(checkbox);
            messageDiv.appendChild(bodyDiv);
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            applySelectionHighlight();
        }

        function appendMessage(role, content, createdAt, messageId) {
            const seq = messagesState.length;
            messagesState.push({
                id: messageId || `temp-${Date.now()}`,
                role,
                content,
                createdAt: createdAt || new Date().toISOString(),
            });
            messageHistory.push({ role, content });
            renderMessageCard(messagesState[messagesState.length - 1], seq);
        }

        function renderGreeting(text) {
            const tip = document.createElement('div');
            tip.className = 'message message-assistant';
            const content = document.createElement('div');
            content.className = 'message-content';
            content.textContent = text;
            tip.appendChild(content);
            chatContainer.appendChild(tip);
        }

        function getSelectedMessages() {
            if (!selectedRange) return [];
            const [start, end] = selectedRange;
            if (start == null || end == null) return [];
            return messagesState
                .slice(Math.min(start, end), Math.max(start, end) + 1)
                .map((m) => ({ role: m.role, content: m.content }));
        }

        function handleSelect(idx) {
            if (!isSelectMode) return;
            if (!selectedRange) {
                selectedRange = [idx, idx];
            } else {
                const [start, end] = selectedRange;
                if (idx < start) {
                    selectedRange = [idx, end];
                } else if (idx > end) {
                    selectedRange = [start, idx];
                } else {
                    selectedRange = [idx, idx];
                }
            }
            persistSelection();
            applySelectionHighlight();
        }

        function applySelectionHighlight() {
            const items = chatContainer.querySelectorAll('.message');
            items.forEach((el) => {
                const idx = Number(el.dataset.index);
                const within =
                    selectedRange && Number.isInteger(idx) && idx >= selectedRange[0] && idx <= selectedRange[1];
                el.classList.toggle('message-selected', Boolean(within));
                el.classList.toggle('select-mode', isSelectMode);
                const checkbox = el.querySelector('.message-select-checkbox');
                if (checkbox) {
                    checkbox.checked = Boolean(within);
                    checkbox.style.display = isSelectMode ? 'block' : 'none';
                }
            });
            if (useSelectedBtn) {
                useSelectedBtn.disabled = !selectedRange;
            }
            if (selectToggle) {
                selectToggle.checked = isSelectMode;
            }
        }

        function persistSelection() {
            if (!currentConversationId) return;
            const key = selectionKey(currentConversationId);
            if (!selectedRange) {
                window.localStorage.removeItem(key);
                return;
            }
            window.localStorage.setItem(key, JSON.stringify(selectedRange));
        }

        function restoreSelection() {
            if (!currentConversationId) return;
            const key = selectionKey(currentConversationId);
            const saved = window.localStorage.getItem(key);
            if (!saved) {
                selectedRange = null;
                applySelectionHighlight();
                return;
            }
            try {
                const parsed = JSON.parse(saved);
                if (
                    Array.isArray(parsed) &&
                    parsed.length === 2 &&
                    messagesState[parsed[0]] !== undefined &&
                    messagesState[parsed[1]] !== undefined
                ) {
                    selectedRange = parsed;
                } else {
                    selectedRange = null;
                }
            } catch (e) {
                selectedRange = null;
            }
            applySelectionHighlight();
        }

        function handleUseSelectedPrompt() {
            const selected = getSelectedMessages();
            if (!selected.length) return;
            const formatted = selected
                .map((m) => `${m.role === 'user' ? 'User' : 'AI'}: ${m.content}`)
                .join('\n');
            const hint = `Please consider the selected conversation:\n${formatted}\n`;
            const existing = messageInput.value.trim();
            messageInput.value = existing ? `${existing}\n\n${hint}` : hint;
            messageInput.focus();
        }

        function showLoading() {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message message-assistant';
            loadingDiv.id = `loading-${Date.now()}`;

            const indicator = document.createElement('div');
            indicator.className = 'loading-indicator';
            for (let i = 0; i < 3; i += 1) {
                const dot = document.createElement('div');
                dot.className = 'loading-dot';
                indicator.appendChild(dot);
            }

            loadingDiv.appendChild(indicator);
            chatContainer.appendChild(loadingDiv);
            return loadingDiv.id;
        }

        function updateMessage(id, content) {
            const messageDiv = document.getElementById(id);
            if (messageDiv) {
                let contentDiv = messageDiv.querySelector('.message-content');
                let timeDiv = messageDiv.querySelector('.message-time');

                if (!contentDiv) {
                    contentDiv = document.createElement('div');
                    contentDiv.className = 'message-content';
                    messageDiv.appendChild(contentDiv);
                }
                if (!timeDiv) {
                    timeDiv = document.createElement('div');
                    timeDiv.className = 'message-time';
                    messageDiv.appendChild(timeDiv);
                }

                contentDiv.textContent = content;
                timeDiv.textContent = new Date().toLocaleTimeString();
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }

        function removeLoading(id) {
            const element = document.getElementById(id);
            if (element) {
                const contentDiv = element.querySelector('.message-content');
                if (contentDiv && contentDiv.textContent === '') {
                    element.remove();
                } else {
                    element.id = '';
                }
            }
        }

        function showError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message error-indicator';
            errorDiv.textContent = message;
            chatContainer.appendChild(errorDiv);
        }
    }

    window.ChatPage = { initChatPage };
})();
