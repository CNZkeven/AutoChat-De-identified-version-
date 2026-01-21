import { useEffect, useMemo, useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { adminService } from '../services/admin';
import { getAgentConfig } from '../utils/constants';
import type {
  AdminAgent,
  AdminConversation,
  AdminRunDetail,
  AdminRunSummary,
  AdminUser,
} from '../types';

type AdminTab = 'users' | 'agents';

export function AdminPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>('agents');
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [agents, setAgents] = useState<AdminAgent[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedStyleId, setSelectedStyleId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<AdminConversation[]>([]);
  const [runs, setRuns] = useState<AdminRunSummary[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [selectedTraceId, setSelectedTraceId] = useState<number | null>(null);
  const [traceDetail, setTraceDetail] = useState<AdminRunDetail | null>(null);
  const [userProfile, setUserProfile] = useState<Record<string, unknown>>({});
  const [userSearch, setUserSearch] = useState('');
  const [debugInput, setDebugInput] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) || null,
    [agents, selectedAgentId]
  );
  const agentConfig = selectedAgentId ? getAgentConfig(selectedAgentId) : undefined;
  const styleOptions = useMemo(() => agentConfig?.styles || [], [agentConfig]);
  const selectedStyle = useMemo(
    () => styleOptions.find((style) => style.id === selectedStyleId) || styleOptions[0],
    [styleOptions, selectedStyleId]
  );

  useEffect(() => {
    if (!styleOptions.length) {
      setSelectedStyleId(null);
      return;
    }
    if (!selectedStyleId || !styleOptions.some((style) => style.id === selectedStyleId)) {
      setSelectedStyleId(styleOptions[0].id);
    }
  }, [selectedStyleId, styleOptions]);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      try {
        const [agentData, userData] = await Promise.all([
          adminService.listAgents(),
          adminService.listUsers(),
        ]);
        setAgents(agentData);
        setUsers(userData);
        const demo = userData.find((user) => user.username === 'demo');
        setSelectedUserId(demo?.id ?? userData[0]?.id ?? null);
        setSelectedAgentId(agentData[0]?.id ?? null);
      } catch (error) {
        setStatusMessage(error instanceof Error ? error.message : '加载失败');
      } finally {
        setIsLoading(false);
      }
    };
    init();
  }, []);

  useEffect(() => {
    if (!selectedUserId) return;
    adminService
      .getUserProfile(selectedUserId)
      .then((profile) => setUserProfile(profile.data || {}))
      .catch(() => setUserProfile({}));
  }, [selectedUserId]);

  useEffect(() => {
    if (!selectedUserId || !selectedAgentId) {
      setConversations([]);
      return;
    }
    setStatusMessage('加载对话中...');
    adminService
      .listConversations(selectedUserId, selectedAgentId)
      .then((data) => {
        setConversations(data);
        const exists = data.some((item) => item.id === selectedConversationId);
        setSelectedConversationId(exists ? selectedConversationId : data[0]?.id ?? null);
        setStatusMessage('');
      })
      .catch((error) => setStatusMessage(error instanceof Error ? error.message : '加载失败'));
  }, [selectedUserId, selectedAgentId, selectedConversationId]);

  useEffect(() => {
    if (!selectedConversationId) {
      setRuns([]);
      setTraceDetail(null);
      return;
    }
    setStatusMessage('加载响应过程...');
    adminService
      .listRuns(selectedConversationId)
      .then((data) => {
        setRuns(data);
        const exists = data.some((item) => item.id === selectedTraceId);
        const nextTraceId = exists ? selectedTraceId : data[0]?.id ?? null;
        setSelectedTraceId(nextTraceId ?? null);
        setStatusMessage('');
      })
      .catch((error) => setStatusMessage(error instanceof Error ? error.message : '加载失败'));
  }, [selectedConversationId, selectedTraceId]);

  useEffect(() => {
    if (!selectedTraceId) {
      setTraceDetail(null);
      return;
    }
    adminService
      .getRunDetail(selectedTraceId)
      .then((data) => {
        setTraceDetail(data);
        setStatusMessage('');
      })
      .catch((error) => setStatusMessage(error instanceof Error ? error.message : '加载失败'));
  }, [selectedTraceId]);

  const handleSearchUsers = async (value: string) => {
    setUserSearch(value);
    try {
      const data = await adminService.listUsers(value);
      setUsers(data);
      const demo = data.find((user) => user.username === 'demo');
      setSelectedUserId(demo?.id ?? data[0]?.id ?? null);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : '加载失败');
    }
  };

  const handleSendDebug = async () => {
    if (!selectedUserId || !selectedAgentId) return;
    const content = debugInput.trim();
    if (!content) {
      setStatusMessage('请输入测试指令');
      return;
    }
    setStatusMessage('调试请求中...');
    try {
      const messages = selectedStyle?.prompt
        ? [
            { role: 'system' as const, content: selectedStyle.prompt },
            { role: 'user' as const, content },
          ]
        : [{ role: 'user' as const, content }];
      const response = await adminService.debugRun({
        user_id: selectedUserId,
        agent: selectedAgentId,
        conversation_id: selectedConversationId ?? undefined,
        messages,
      });
      setDebugInput('');
      setSelectedConversationId(response.conversation_id);
      setSelectedTraceId(response.trace_id);
      setStatusMessage(response.final_text ? '调试完成' : '调试完成（无回复）');
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : '调试失败');
    }
  };

  const formatDate = (value?: string | null) => {
    if (!value) return '未知';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  };

  return (
    <Layout title="管理员调试">
      <div className="min-h-[calc(100vh-4rem)] bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
        <div className="container mx-auto px-4 py-8">
          <div className="flex gap-3 mb-6">
            <button
              type="button"
              className={`px-4 py-2 rounded-full text-sm transition ${
                activeTab === 'users'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white/10 text-slate-200 hover:bg-white/20'
              }`}
              onClick={() => setActiveTab('users')}
            >
              用户管理
            </button>
            <button
              type="button"
              className={`px-4 py-2 rounded-full text-sm transition ${
                activeTab === 'agents'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white/10 text-slate-200 hover:bg-white/20'
              }`}
              onClick={() => setActiveTab('agents')}
            >
              智能体管理
            </button>
          </div>

          {activeTab === 'users' ? (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">用户管理</h2>
                <span className="text-xs px-2 py-1 rounded-full bg-slate-800 text-slate-300">
                  占位
                </span>
              </div>
              <p className="text-sm text-slate-300">
                用户管理模块建设中，用于后续权限、状态与批量操作管理。
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-[260px_320px_1fr] gap-6">
              <div className="space-y-6">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold">测试用户</h3>
                    <span className="text-xs px-2 py-1 rounded-full bg-blue-500/20 text-blue-200">
                      默认 demo
                    </span>
                  </div>
                  <label className="block text-xs text-slate-300 mb-2">搜索用户名</label>
                  <input
                    type="text"
                    value={userSearch}
                    onChange={(e) => handleSearchUsers(e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                    placeholder="输入用户名筛选"
                  />
                  <label className="block text-xs text-slate-300 mt-4 mb-2">选择用户</label>
                  <select
                    className="w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                    value={selectedUserId ?? ''}
                    onChange={(e) => setSelectedUserId(Number(e.target.value))}
                    disabled={isLoading || users.length === 0}
                  >
                    {users.length === 0 ? (
                      <option value="">暂无用户</option>
                    ) : (
                      users.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.username} (#{user.id})
                        </option>
                      ))
                    )}
                  </select>
                  <div className="mt-3 text-xs text-slate-400">
                    当前用户：{selectedUserId ?? '未选择'}
                  </div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <h3 className="text-sm font-semibold mb-3">智能体与风格</h3>
                  <label className="block text-xs text-slate-300 mb-2">智能体</label>
                  <select
                    className="w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                    value={selectedAgentId ?? ''}
                    onChange={(e) => setSelectedAgentId(e.target.value)}
                    disabled={agents.length === 0}
                  >
                    {agents.length === 0 ? (
                      <option value="">暂无智能体</option>
                    ) : (
                      agents.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.title || agent.id}
                        </option>
                      ))
                    )}
                  </select>
                  <label className="block text-xs text-slate-300 mt-4 mb-2">风格</label>
                  <select
                    className="w-full rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                    value={selectedStyle?.id ?? ''}
                    onChange={(e) => setSelectedStyleId(e.target.value)}
                    disabled={!styleOptions.length}
                  >
                    {styleOptions.map((style) => (
                      <option key={style.id} value={style.id}>
                        {style.name}
                      </option>
                    ))}
                  </select>
                  <div className="mt-3 text-xs text-slate-400">
                    提示词模板位置：{selectedAgent?.prompt_template_path || '未配置'}
                  </div>
                  <div className="mt-3 text-xs text-slate-300">系统提示词</div>
                  <pre className="mt-2 max-h-36 overflow-auto rounded-lg bg-slate-900/80 p-3 text-[11px] text-slate-200">
                    {selectedAgent?.prompt || '未配置提示词'}
                  </pre>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold">个人设置/能力分析</h3>
                    <span className="text-xs px-2 py-1 rounded-full bg-slate-800 text-slate-300">
                      扩展
                    </span>
                  </div>
                  <pre className="max-h-40 overflow-auto rounded-lg bg-slate-900/80 p-3 text-[11px] text-slate-200">
                    {JSON.stringify(userProfile, null, 2) || '暂无数据'}
                  </pre>
                </div>
              </div>

              <div className="space-y-6">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <h3 className="text-sm font-semibold mb-3">对话列表</h3>
                  <div className="space-y-2 max-h-64 overflow-auto">
                    {conversations.length === 0 ? (
                      <div className="text-xs text-slate-400">暂无对话</div>
                    ) : (
                      conversations.map((convo) => (
                        <button
                          key={convo.id}
                          type="button"
                          className={`w-full text-left rounded-xl border px-3 py-2 text-xs transition ${
                            convo.id === selectedConversationId
                              ? 'border-blue-500 bg-blue-500/10'
                              : 'border-white/10 bg-white/5 hover:bg-white/10'
                          }`}
                          onClick={() => setSelectedConversationId(convo.id)}
                        >
                          <div className="font-semibold text-slate-100">{convo.title || '未命名对话'}</div>
                          <div className="text-slate-400 mt-1">
                            更新时间：{formatDate(convo.updated_at || convo.created_at)}
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <h3 className="text-sm font-semibold mb-3">响应过程（用户指令）</h3>
                  <div className="space-y-2 max-h-64 overflow-auto">
                    {runs.length === 0 ? (
                      <div className="text-xs text-slate-400">暂无响应过程</div>
                    ) : (
                      runs.map((run) => (
                        <button
                          key={run.id}
                          type="button"
                          className={`w-full text-left rounded-xl border px-3 py-2 text-xs transition ${
                            run.id === selectedTraceId
                              ? 'border-emerald-400 bg-emerald-400/10'
                              : 'border-white/10 bg-white/5 hover:bg-white/10'
                          }`}
                          onClick={() => setSelectedTraceId(run.id)}
                        >
                          <div className="font-semibold text-slate-100">
                            {run.request_text || '（空指令）'}
                          </div>
                          <div className="text-slate-400 mt-1">时间：{formatDate(run.created_at)}</div>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <h3 className="text-sm font-semibold mb-2">完整指令与响应</h3>
                  <div className="text-xs text-slate-400 mb-3">
                    当前指令：{traceDetail?.request_text || '暂无'}
                  </div>
                  <div className="space-y-3 max-h-[520px] overflow-auto pr-1">
                    {traceDetail?.trace?.length ? (
                      traceDetail.trace.map((event, index) => (
                        <div
                          key={`${index}-${JSON.stringify(event).length}`}
                          className="rounded-xl border border-white/10 bg-slate-900/70 p-3"
                        >
                          <div className="flex items-center justify-between text-xs text-slate-300 mb-2">
                            <span className="font-semibold">
                              {typeof event.seq === 'number' ? `${event.seq}. ` : ''}
                              {String(event.type || 'event')}
                            </span>
                            <span>
                              {event.source ? String(event.source) : ''}{' '}
                              {event.stage ? `· ${event.stage}` : ''}
                            </span>
                          </div>
                          <pre className="text-[11px] text-slate-200 whitespace-pre-wrap break-words">
                            {JSON.stringify(event, null, 2)}
                          </pre>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-slate-400">暂无追踪数据</div>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <h3 className="text-sm font-semibold mb-2">调试输入</h3>
                  <textarea
                    value={debugInput}
                    onChange={(e) => setDebugInput(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-sm text-white min-h-[100px]"
                    placeholder="输入测试指令"
                  />
                  <div className="flex items-center gap-3 mt-3">
                    <button
                      type="button"
                      onClick={handleSendDebug}
                      className="px-4 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm"
                      disabled={!selectedUserId || !selectedAgentId}
                    >
                      发送调试
                    </button>
                    <span className="text-xs text-slate-400">{statusMessage}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
