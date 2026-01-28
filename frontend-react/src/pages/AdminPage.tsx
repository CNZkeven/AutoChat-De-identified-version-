import { useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import { Layout } from '../components/layout/Layout';
import { adminService } from '../services/admin';
import { getAgentConfig } from '../utils/constants';
import type {
  AdminAgent,
  AdminConversation,
  AdminRunDetail,
  AdminRunSummary,
  AdminUser,
  AdminUserProfiles,
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

  const [userSearchInput, setUserSearchInput] = useState('');
  const [userFilters, setUserFilters] = useState<{ major: string; grade: string; gender: string }>({
    major: '',
    grade: '',
    gender: '',
  });
  const [filterOptions, setFilterOptions] = useState<{ majors: string[]; grades: number[]; genders: string[] }>({
    majors: [],
    grades: [],
    genders: [],
  });
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [userProfiles, setUserProfiles] = useState<AdminUserProfiles | null>(null);
  const [userEdit, setUserEdit] = useState<Partial<AdminUser>>({});
  const [userStatusMessage, setUserStatusMessage] = useState('');
  const [importResult, setImportResult] = useState<string>('');
  const [userModalTab, setUserModalTab] = useState<'base' | 'profile'>('base');
  const importInputRef = useRef<HTMLInputElement | null>(null);

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
        const [agentData, userData, filters] = await Promise.all([
          adminService.listAgents(),
          adminService.listUsers(),
          adminService.listUserFilters(),
        ]);
        setAgents(agentData);
        setUsers(userData);
        setFilterOptions(filters);
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

  useEffect(() => {
    if (activeTab !== 'users') return;
    loadManagedUsers();
    adminService.listUserFilters().then(setFilterOptions).catch(() => undefined);
  }, [activeTab]);

  const handleSearchUsers = async (value: string) => {
    setUserSearch(value);
    try {
      const data = await adminService.listUsers({ q: value });
      setUsers(data);
      const demo = data.find((user) => user.username === 'demo');
      setSelectedUserId(demo?.id ?? data[0]?.id ?? null);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : '加载失败');
    }
  };

  const loadManagedUsers = async (params?: { q?: string; major?: string; grade?: number; gender?: string }) => {
    try {
      const data = await adminService.listUsers(params);
      setUsers(data);
    } catch (error) {
      setUserStatusMessage(error instanceof Error ? error.message : '加载失败');
    }
  };

  const handleUserSearch = async () => {
    setUserStatusMessage('加载中...');
    await loadManagedUsers({
      q: userSearchInput || undefined,
      major: userFilters.major || undefined,
      grade: userFilters.grade ? Number(userFilters.grade) : undefined,
      gender: userFilters.gender || undefined,
    });
    setUserStatusMessage('');
  };

  const handleOpenUserModal = async (user: AdminUser) => {
    setSelectedUser(user);
    setUserEdit(user);
    setUserModalOpen(true);
    setUserModalTab('base');
    try {
      const profiles = await adminService.getUserProfiles(user.id);
      setUserProfiles(profiles);
    } catch {
      setUserProfiles(null);
    }
  };

  const handleSaveUser = async () => {
    if (!selectedUser) return;
    setUserStatusMessage('保存中...');
    try {
      const updated = await adminService.updateUser(selectedUser.id, {
        email: userEdit.email ?? null,
        full_name: userEdit.full_name ?? null,
        major: userEdit.major ?? null,
        grade: userEdit.grade ?? null,
        gender: userEdit.gender ?? null,
        is_active: userEdit.is_active ?? null,
      });
      setSelectedUser(updated);
      setUsers((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      setUserStatusMessage('保存完成');
    } catch (error) {
      setUserStatusMessage(error instanceof Error ? error.message : '保存失败');
    }
  };

  const handleResetPassword = async () => {
    if (!selectedUser) return;
    setUserStatusMessage('重置密码中...');
    try {
      await adminService.resetUserPassword(selectedUser.id);
      setUserStatusMessage('已重置为学号');
    } catch (error) {
      setUserStatusMessage(error instanceof Error ? error.message : '重置失败');
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const blob = await adminService.downloadImportTemplate();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = '用户导入模板.xlsx';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setUserStatusMessage(error instanceof Error ? error.message : '下载失败');
    }
  };

  const handleImportClick = () => {
    importInputRef.current?.click();
  };

  const handleImportFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUserStatusMessage('导入中...');
    try {
      const result = await adminService.importUsers(file);
      setImportResult(`导入完成：新增 ${result.created}，更新 ${result.updated}`);
      await loadManagedUsers();
      setUserStatusMessage('');
    } catch (error) {
      setUserStatusMessage(error instanceof Error ? error.message : '导入失败');
    } finally {
      event.target.value = '';
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
            <div className="space-y-6">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-6 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-lg font-semibold">用户管理</h2>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="px-3 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700"
                      onClick={handleDownloadTemplate}
                    >
                      下载模板
                    </button>
                    <button
                      type="button"
                      className="px-3 py-2 rounded-lg bg-blue-500/20 text-blue-100 hover:bg-blue-500/30"
                      onClick={handleImportClick}
                    >
                      批量导入
                    </button>
                    <input
                      ref={importInputRef}
                      type="file"
                      accept=".xlsx"
                      className="hidden"
                      onChange={handleImportFileChange}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <input
                    type="text"
                    value={userSearchInput}
                    onChange={(event) => setUserSearchInput(event.target.value)}
                    className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                    placeholder="搜索学号或姓名"
                  />
                  <select
                    className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                    value={userFilters.major}
                    onChange={(event) => setUserFilters((prev) => ({ ...prev, major: event.target.value }))}
                  >
                    <option value="">全部专业</option>
                    {filterOptions.majors.map((major) => (
                      <option key={major} value={major}>
                        {major}
                      </option>
                    ))}
                  </select>
                  <select
                    className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                    value={userFilters.grade}
                    onChange={(event) => setUserFilters((prev) => ({ ...prev, grade: event.target.value }))}
                  >
                    <option value="">全部年级</option>
                    {filterOptions.grades.map((grade) => (
                      <option key={grade} value={String(grade)}>
                        {grade}级
                      </option>
                    ))}
                  </select>
                  <select
                    className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                    value={userFilters.gender}
                    onChange={(event) => setUserFilters((prev) => ({ ...prev, gender: event.target.value }))}
                  >
                    <option value="">全部性别</option>
                    {filterOptions.genders.map((gender) => (
                      <option key={gender} value={gender}>
                        {gender}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    className="px-3 py-2 rounded-lg bg-emerald-500/20 text-emerald-100 hover:bg-emerald-500/30"
                    onClick={handleUserSearch}
                  >
                    搜索
                  </button>
                  <button
                    type="button"
                    className="px-3 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700"
                    onClick={() => {
                      setUserSearchInput('');
                      setUserFilters({ major: '', grade: '', gender: '' });
                      loadManagedUsers();
                    }}
                  >
                    重置
                  </button>
                  {userStatusMessage && <span className="text-xs text-slate-400">{userStatusMessage}</span>}
                  {importResult && <span className="text-xs text-emerald-300">{importResult}</span>}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="text-slate-300">
                      <tr>
                        <th className="px-3 py-2 text-left">学号</th>
                        <th className="px-3 py-2 text-left">姓名</th>
                        <th className="px-3 py-2 text-left">专业</th>
                        <th className="px-3 py-2 text-left">年级</th>
                        <th className="px-3 py-2 text-left">性别</th>
                        <th className="px-3 py-2 text-left">邮箱</th>
                      </tr>
                    </thead>
                    <tbody className="text-slate-200">
                      {users.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-3 py-4 text-slate-400">
                            暂无用户数据
                          </td>
                        </tr>
                      ) : (
                        users.map((user) => (
                          <tr
                            key={user.id}
                            className="border-t border-white/5 hover:bg-white/5 cursor-pointer"
                            onClick={() => handleOpenUserModal(user)}
                          >
                            <td className="px-3 py-2">{user.username}</td>
                            <td className="px-3 py-2">{user.full_name || '-'}</td>
                            <td className="px-3 py-2">{user.major || '-'}</td>
                            <td className="px-3 py-2">{user.grade ? `${user.grade}级` : '-'}</td>
                            <td className="px-3 py-2">{user.gender || '-'}</td>
                            <td className="px-3 py-2">{user.email || '-'}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {userModalOpen && selectedUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
                  <div className="w-full max-w-3xl rounded-2xl border border-white/10 bg-slate-900 p-6 text-slate-100">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold">用户详情</h3>
                      <button
                        type="button"
                        className="text-slate-400 hover:text-slate-200"
                        onClick={() => setUserModalOpen(false)}
                      >
                        关闭
                      </button>
                    </div>

                    <div className="flex gap-3 mt-4">
                      <button
                        type="button"
                        className={`px-3 py-1.5 rounded-full text-xs ${
                          userModalTab === 'base'
                            ? 'bg-blue-500 text-white'
                            : 'bg-white/10 text-slate-200 hover:bg-white/20'
                        }`}
                        onClick={() => setUserModalTab('base')}
                      >
                        基本信息
                      </button>
                      <button
                        type="button"
                        className={`px-3 py-1.5 rounded-full text-xs ${
                          userModalTab === 'profile'
                            ? 'bg-blue-500 text-white'
                            : 'bg-white/10 text-slate-200 hover:bg-white/20'
                        }`}
                        onClick={() => setUserModalTab('profile')}
                      >
                        用户画像
                      </button>
                    </div>

                    {userModalTab === 'base' ? (
                      <div className="mt-4 space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                          <label className="flex flex-col gap-1">
                            <span className="text-xs text-slate-400">学号</span>
                            <input
                              value={selectedUser.username}
                              readOnly
                              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200"
                            />
                          </label>
                          <label className="flex flex-col gap-1">
                            <span className="text-xs text-slate-400">姓名</span>
                            <input
                              value={userEdit.full_name ?? ''}
                              onChange={(event) =>
                                setUserEdit((prev) => ({ ...prev, full_name: event.target.value }))
                              }
                              className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                            />
                          </label>
                          <label className="flex flex-col gap-1">
                            <span className="text-xs text-slate-400">专业</span>
                            <input
                              value={userEdit.major ?? ''}
                              onChange={(event) =>
                                setUserEdit((prev) => ({ ...prev, major: event.target.value }))
                              }
                              className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                            />
                          </label>
                          <label className="flex flex-col gap-1">
                            <span className="text-xs text-slate-400">年级</span>
                            <input
                              value={userEdit.grade ?? ''}
                              onChange={(event) =>
                                setUserEdit((prev) => ({
                                  ...prev,
                                  grade: event.target.value ? Number(event.target.value) : null,
                                }))
                              }
                              className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                            />
                          </label>
                          <label className="flex flex-col gap-1">
                            <span className="text-xs text-slate-400">性别</span>
                            <select
                              value={userEdit.gender ?? ''}
                              onChange={(event) =>
                                setUserEdit((prev) => ({ ...prev, gender: event.target.value }))
                              }
                              className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                            >
                              <option value="">未设置</option>
                              <option value="男">男</option>
                              <option value="女">女</option>
                              <option value="未知">未知</option>
                            </select>
                          </label>
                          <label className="flex flex-col gap-1">
                            <span className="text-xs text-slate-400">邮箱</span>
                            <input
                              value={userEdit.email ?? ''}
                              onChange={(event) =>
                                setUserEdit((prev) => ({ ...prev, email: event.target.value }))
                              }
                              className="rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-sm text-white"
                            />
                          </label>
                        </div>

                        <div className="flex flex-wrap items-center gap-3">
                          <button
                            type="button"
                            className="px-3 py-2 rounded-lg bg-emerald-500/20 text-emerald-100 hover:bg-emerald-500/30"
                            onClick={handleSaveUser}
                          >
                            保存
                          </button>
                          <button
                            type="button"
                            className="px-3 py-2 rounded-lg bg-amber-500/20 text-amber-100 hover:bg-amber-500/30"
                            onClick={handleResetPassword}
                          >
                            重置密码为学号
                          </button>
                          {userStatusMessage && (
                            <span className="text-xs text-slate-400">{userStatusMessage}</span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="mt-4 space-y-4 text-sm">
                        <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                          <div className="text-xs text-slate-400 mb-2">系统画像（仅管理员可见）</div>
                          <div className="whitespace-pre-wrap text-slate-200">
                            {userProfiles?.system_profile || '暂无系统画像'}
                          </div>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                          <div className="text-xs text-slate-400 mb-2">用户画像</div>
                          <div className="whitespace-pre-wrap text-slate-200">
                            {userProfiles?.public_profile || '暂无用户画像'}
                          </div>
                        </div>
                        <button
                          type="button"
                          className="px-3 py-2 rounded-lg bg-blue-500/20 text-blue-100 hover:bg-blue-500/30"
                          onClick={() =>
                            window.open(`/admin/users/${selectedUser.id}/academics`, '_blank')
                          }
                        >
                          查看学业情况
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
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
