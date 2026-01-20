document.addEventListener('DOMContentLoaded', () => {
    if (!window.Auth || !window.APP_CONFIG) return;

    const userSearchEl = document.getElementById('user-search');
    const userSelectEl = document.getElementById('user-select');
    const userMetaEl = document.getElementById('user-meta');
    const userProfileEl = document.getElementById('user-profile');
    const agentSelectEl = document.getElementById('agent-select');
    const styleSelectEl = document.getElementById('style-select');
    const promptLocationEl = document.getElementById('prompt-location');
    const agentPromptEl = document.getElementById('agent-prompt');
    const conversationListEl = document.getElementById('conversation-list');
    const conversationStatusEl = document.getElementById('conversation-status');
    const runListEl = document.getElementById('run-list');
    const runStatusEl = document.getElementById('run-status');
    const traceListEl = document.getElementById('trace-list');
    const traceHeaderEl = document.getElementById('trace-header');
    const debugInputEl = document.getElementById('debug-input');
    const debugSendEl = document.getElementById('debug-send');
    const debugStatusEl = document.getElementById('debug-status');

    const tabs = Array.from(document.querySelectorAll('.admin-tab'));
    const panels = Array.from(document.querySelectorAll('.admin-tab-panel'));

    const state = {
        users: [],
        agents: [],
        selectedUserId: null,
        selectedAgent: null,
        selectedStyle: null,
        selectedConversationId: null,
        selectedTraceId: null,
    };

    function setStatus(el, message = '', type = '') {
        if (!el) return;
        el.textContent = message;
        el.classList.remove('status-error');
        if (type === 'error') {
            el.classList.add('status-error');
        }
    }

    async function apiJson(path, options) {
        const response = await window.Auth.apiFetch(path, options);
        const data = await response.json();
        if (!response.ok) {
            const detail = data.detail || data.message || '请求失败';
            throw new Error(detail);
        }
        return data;
    }

    function switchTab(tabName) {
        tabs.forEach((tab) => {
            const active = tab.dataset.tab === tabName;
            tab.classList.toggle('active', active);
        });
        panels.forEach((panel) => {
            panel.classList.toggle('active', panel.id === `admin-${tabName}`);
        });
    }

    function renderUsers() {
        if (!userSelectEl) return;
        userSelectEl.innerHTML = '';
        if (!state.users || state.users.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = '暂无用户';
            option.disabled = true;
            userSelectEl.appendChild(option);
            return;
        }
        state.users.forEach((user) => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = `${user.username} (#${user.id})`;
            userSelectEl.appendChild(option);
        });
        if (state.selectedUserId) {
            userSelectEl.value = state.selectedUserId;
        }
    }

    function renderAgents() {
        if (!agentSelectEl) return;
        agentSelectEl.innerHTML = '';
        if (!state.agents || state.agents.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = '暂无智能体';
            option.disabled = true;
            agentSelectEl.appendChild(option);
            return;
        }
        state.agents.forEach((agent) => {
            const option = document.createElement('option');
            option.value = agent.id;
            option.textContent = agent.title || agent.id;
            agentSelectEl.appendChild(option);
        });
        if (state.selectedAgent) {
            agentSelectEl.value = state.selectedAgent;
        }
    }

    function renderStyles() {
        if (!styleSelectEl) return;
        styleSelectEl.innerHTML = '';
        const agent = state.agents.find((item) => item.id === state.selectedAgent);
        const styles = [];
        if (agent && agent.profile && agent.profile.template) {
            styles.push(agent.profile.template);
        }
        styles.push('默认');
        const unique = Array.from(new Set(styles));
        unique.forEach((style) => {
            const option = document.createElement('option');
            option.value = style;
            option.textContent = style;
            styleSelectEl.appendChild(option);
        });
        if (!unique.includes(state.selectedStyle)) {
            state.selectedStyle = unique[0] || null;
        }
        styleSelectEl.value = state.selectedStyle || '';
        if (promptLocationEl) {
            promptLocationEl.textContent = agent
                ? `提示词模板位置：${agent.prompt_template_path || '未配置'}`
                : '';
        }
        if (agentPromptEl) {
            agentPromptEl.textContent = agent && agent.prompt ? agent.prompt : '未配置提示词';
        }
    }

    function renderConversations(conversations) {
        if (!conversationListEl) return;
        conversationListEl.innerHTML = '';
        if (!conversations || conversations.length === 0) {
            conversationListEl.innerHTML = '<div class="admin-muted">暂无对话</div>';
            return;
        }
        conversations.forEach((convo) => {
            const item = document.createElement('div');
            item.className = 'admin-item';
            if (convo.id === state.selectedConversationId) {
                item.classList.add('active');
            }
            item.dataset.id = convo.id;
            item.innerHTML = `
                <div class="admin-item-title">${convo.title || '未命名对话'}</div>
                <div class="admin-item-meta">更新时间：${formatDate(convo.updated_at || convo.created_at)}</div>
            `;
            item.addEventListener('click', () => {
                state.selectedConversationId = convo.id;
                state.selectedTraceId = null;
                traceHeaderEl.textContent = '';
                traceListEl.innerHTML = '';
                loadRuns();
                renderConversations(conversations);
            });
            conversationListEl.appendChild(item);
        });
    }

    function renderRuns(runs) {
        if (!runListEl) return;
        runListEl.innerHTML = '';
        if (!runs || runs.length === 0) {
            runListEl.innerHTML = '<div class="admin-muted">暂无响应过程</div>';
            return;
        }
        runs.forEach((run) => {
            const item = document.createElement('div');
            item.className = 'admin-item';
            if (run.id === state.selectedTraceId) {
                item.classList.add('active');
            }
            item.dataset.id = run.id;
            item.innerHTML = `
                <div class="admin-item-title">${run.request_text || '（空指令）'}</div>
                <div class="admin-item-meta">时间：${formatDate(run.created_at)}</div>
            `;
            item.addEventListener('click', () => {
                state.selectedTraceId = run.id;
                loadTrace(run.id);
                renderRuns(runs);
            });
            runListEl.appendChild(item);
        });
    }

    function renderTrace(trace) {
        if (!traceListEl) return;
        traceListEl.innerHTML = '';
        if (!trace || trace.length === 0) {
            traceListEl.innerHTML = '<div class="admin-muted">暂无追踪数据</div>';
            return;
        }
        trace.forEach((event) => {
            const card = document.createElement('div');
            card.className = 'admin-trace-item';
            const header = document.createElement('div');
            header.className = 'admin-trace-header';
            const label = `${event.seq || ''} ${event.type || ''}`.trim();
            header.innerHTML = `
                <span class="admin-trace-title">${label}</span>
                <span class="admin-trace-meta">${event.source || ''}${event.stage ? ` · ${event.stage}` : ''}</span>
            `;
            const body = document.createElement('pre');
            body.className = 'admin-code';
            const payload = { ...event };
            delete payload.seq;
            body.textContent = JSON.stringify(payload, null, 2);
            card.appendChild(header);
            card.appendChild(body);
            traceListEl.appendChild(card);
        });
    }

    function formatDate(value) {
        if (!value) return '未知';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleString();
    }

    async function ensureAdmin() {
        try {
            await apiJson('/api/admin/me');
        } catch (error) {
            alert('需要管理员权限访问。');
            window.location.href = 'index.html';
        }
    }

    async function loadAgents() {
        const agents = await apiJson('/api/admin/agents');
        state.agents = agents || [];
        state.selectedAgent = state.agents[0]?.id || null;
        renderAgents();
        renderStyles();
    }

    async function loadUsers(query = '') {
        const users = await apiJson(`/api/admin/users${query ? `?q=${encodeURIComponent(query)}` : ''}`);
        state.users = users || [];
        const demo = state.users.find((user) => user.username === 'demo');
        state.selectedUserId = demo ? demo.id : state.users[0]?.id || null;
        renderUsers();
        if (state.selectedUserId) {
            await loadUserProfile();
            await loadConversations();
        } else {
            renderConversations([]);
            renderRuns([]);
            renderTrace([]);
        }
    }

    async function loadUserProfile() {
        if (!state.selectedUserId || !userProfileEl) return;
        const profile = await apiJson(`/api/admin/users/${state.selectedUserId}/profile`);
        const user = state.users.find((item) => item.id === state.selectedUserId);
        if (userMetaEl) {
            userMetaEl.textContent = user
                ? `用户：${user.username} (#${user.id})`
                : `用户ID：${state.selectedUserId}`;
        }
        userProfileEl.textContent = JSON.stringify(profile.data || {}, null, 2) || '暂无数据';
    }

    async function loadConversations() {
        if (!state.selectedUserId || !state.selectedAgent) return;
        setStatus(conversationStatusEl, '加载中...');
        try {
            const conversations = await apiJson(
                `/api/admin/users/${state.selectedUserId}/agents/${state.selectedAgent}/conversations`
            );
            const exists = conversations.some((item) => item.id === state.selectedConversationId);
            state.selectedConversationId = exists ? state.selectedConversationId : conversations[0]?.id || null;
            renderConversations(conversations);
            await loadRuns();
            setStatus(conversationStatusEl, '');
        } catch (error) {
            setStatus(conversationStatusEl, error.message, 'error');
        }
    }

    async function loadRuns() {
        if (!state.selectedConversationId) {
            renderRuns([]);
            setStatus(runStatusEl, '请选择对话');
            return;
        }
        setStatus(runStatusEl, '加载中...');
        try {
            const runs = await apiJson(`/api/admin/conversations/${state.selectedConversationId}/runs`);
            const exists = runs.some((item) => item.id === state.selectedTraceId);
            state.selectedTraceId = exists ? state.selectedTraceId : runs[0]?.id || null;
            renderRuns(runs);
            if (state.selectedTraceId) {
                await loadTrace(state.selectedTraceId);
            } else {
                renderTrace([]);
            }
            setStatus(runStatusEl, '');
        } catch (error) {
            setStatus(runStatusEl, error.message, 'error');
        }
    }

    async function loadTrace(traceId) {
        if (!traceId) return;
        try {
            const trace = await apiJson(`/api/admin/runs/${traceId}`);
            traceHeaderEl.textContent = trace.request_text
                ? `当前指令：${trace.request_text}`
                : '当前指令：暂无';
            renderTrace(trace.trace || []);
        } catch (error) {
            renderTrace([]);
            traceHeaderEl.textContent = error.message;
        }
    }

    async function sendDebug() {
        if (!state.selectedUserId || !state.selectedAgent) return;
        const message = (debugInputEl.value || '').trim();
        if (!message) {
            setStatus(debugStatusEl, '请输入测试指令', 'error');
            return;
        }
        setStatus(debugStatusEl, '发送中...');
        debugSendEl.disabled = true;
        try {
            const payload = {
                user_id: state.selectedUserId,
                agent: state.selectedAgent,
                style: state.selectedStyle,
                conversation_id: state.selectedConversationId,
                message,
            };
            const result = await apiJson('/api/admin/debug/run', {
                method: 'POST',
                body: JSON.stringify(payload),
            });
            debugInputEl.value = '';
            state.selectedConversationId = result.conversation_id;
            state.selectedTraceId = result.trace_id;
            await loadConversations();
            if (state.selectedTraceId) {
                await loadTrace(state.selectedTraceId);
            }
            setStatus(debugStatusEl, result.final_text ? '调试完成' : '调试完成（无回复）');
        } catch (error) {
            setStatus(debugStatusEl, error.message, 'error');
        } finally {
            debugSendEl.disabled = false;
        }
    }

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    if (userSearchEl) {
        userSearchEl.addEventListener('input', (event) => {
            const value = event.target.value.trim();
            loadUsers(value);
        });
    }

    if (userSelectEl) {
        userSelectEl.addEventListener('change', async () => {
            state.selectedUserId = parseInt(userSelectEl.value, 10);
            await loadUserProfile();
            await loadConversations();
        });
    }

    if (agentSelectEl) {
        agentSelectEl.addEventListener('change', async () => {
            state.selectedAgent = agentSelectEl.value;
            renderStyles();
            await loadConversations();
        });
    }

    if (styleSelectEl) {
        styleSelectEl.addEventListener('change', () => {
            state.selectedStyle = styleSelectEl.value;
        });
    }

    if (debugSendEl) {
        debugSendEl.addEventListener('click', sendDebug);
    }

    window.Auth.initNav();
    window.Auth.requireAuth();
    ensureAdmin()
        .then(loadAgents)
        .then(loadUsers)
        .catch((error) => {
            setStatus(debugStatusEl, error.message, 'error');
        });
});
