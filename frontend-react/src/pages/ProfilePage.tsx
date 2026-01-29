import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { authService } from '../services/auth';
import { profileService } from '../services/profile';
import { useAuthStore } from '../store/authStore';
import type {
  UserAcademicReport,
  UserCourse,
  UserGraduationRequirement,
  UserProfile,
} from '../types';

type ProfileTab = 'base' | 'profile' | 'academics' | 'requirements' | 'report';
type RequirementItem = {
  id: number;
  index?: string;
  description: string;
  achieved?: boolean;
  achievement_rate?: number | null;
  parent_id?: number | null;
  level?: number | null;
  children?: RequirementItem[];
};

const parseIndexParts = (value?: string | number) => {
  if (value === null || value === undefined) return [];
  const matches = String(value).match(/\d+/g);
  return matches ? matches.map((item) => Number(item)) : [];
};

const compareIndexParts = (a?: string | number, b?: string | number) => {
  const partsA = parseIndexParts(a);
  const partsB = parseIndexParts(b);
  if (partsA.length === 0 && partsB.length === 0) return 0;
  if (partsA.length === 0) return 1;
  if (partsB.length === 0) return -1;
  const maxLength = Math.max(partsA.length, partsB.length);
  for (let i = 0; i < maxLength; i += 1) {
    const valueA = partsA[i] ?? 0;
    const valueB = partsB[i] ?? 0;
    if (valueA !== valueB) {
      return valueA - valueB;
    }
  }
  return 0;
};

export function ProfilePage() {
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedTab, setSelectedTab] = useState<ProfileTab | null>(null);
  const [publicProfile, setPublicProfile] = useState<UserProfile | null>(null);
  const [courses, setCourses] = useState<UserCourse[]>([]);
  const [requirements, setRequirements] = useState<UserGraduationRequirement | null>(null);
  const [academicReport, setAcademicReport] = useState<UserAcademicReport | null>(null);
  const [status, setStatus] = useState('');
  const [expandedRequirements, setExpandedRequirements] = useState<Record<number, boolean>>({});

  const queryTab = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const tab = params.get('tab');
    const allowedTabs: ProfileTab[] = ['base', 'profile', 'academics', 'requirements', 'report'];
    return tab && allowedTabs.includes(tab as ProfileTab) ? (tab as ProfileTab) : null;
  }, [location.search]);

  const activeTab = selectedTab ?? queryTab ?? 'base';

  useEffect(() => {
    authService.getCurrentUser().then(setUser).catch(() => undefined);
  }, [setUser]);

  useEffect(() => {
    if (activeTab === 'profile') {
      profileService.getPublicProfile().then(setPublicProfile).catch(() => undefined);
    }
    if (activeTab === 'academics') {
      profileService.listAcademics().then(setCourses).catch(() => undefined);
    }
    if (activeTab === 'requirements') {
      profileService.getGraduationRequirements().then(setRequirements).catch(() => undefined);
    }
    if (activeTab === 'report') {
      profileService.getAcademicReport().then(setAcademicReport).catch(() => undefined);
    }
  }, [activeTab]);

  const infoRows = useMemo(
    () => [
      { label: '学号', value: user?.username || '-' },
      { label: '姓名', value: user?.full_name || '-' },
      { label: '专业', value: user?.major || '-' },
      { label: '年级', value: user?.grade ? `${user.grade}级` : '-' },
      { label: '性别', value: user?.gender || '-' },
      { label: '邮箱', value: user?.email || '-' },
    ],
    [user]
  );

  const formatPercentile = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    return `${(value * 100).toFixed(1)}%`;
  };

  const groupedRequirements = useMemo(() => {
    const raw =
      (requirements?.data as { requirements_grouped?: unknown[] } | undefined)
        ?.requirements_grouped || [];
    return raw as RequirementItem[];
  }, [requirements]);

  const sortedGroupedRequirements = useMemo(
    () =>
      [...groupedRequirements]
        .sort((left, right) => compareIndexParts(left.index ?? left.id, right.index ?? right.id))
        .map((item) => ({
          ...item,
          children: [...(item.children ?? [])].sort((left, right) =>
            compareIndexParts(left.index ?? left.id, right.index ?? right.id)
          ),
        })),
    [groupedRequirements]
  );

  const handleGenerateProfile = async () => {
    setStatus('生成画像中...');
    try {
      const data = await profileService.generatePublicProfile();
      setPublicProfile(data);
      setStatus('生成完成');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '生成失败');
    }
  };

  const handleRefreshRequirements = async () => {
    setStatus('更新毕业要求中...');
    try {
      const data = await profileService.refreshGraduationRequirements();
      setRequirements(data);
      setStatus('更新完成');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '更新失败');
    }
  };

  const handleGenerateAcademicReport = async () => {
    setStatus('生成学业报告中...');
    try {
      const data = await profileService.generateAcademicReport();
      setAcademicReport(data);
      setStatus('生成完成');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '生成失败');
    }
  };

  const toggleRequirement = (requirementId: number) => {
    setExpandedRequirements((prev) => ({
      ...prev,
      [requirementId]: !prev[requirementId],
    }));
  };

  return (
    <Layout title="个人中心">
      <div className="min-h-[calc(100vh-4rem)]">
        <div className="container mx-auto px-4 py-8 space-y-6">
          <div className="flex flex-wrap gap-3">
            {(
              [
                { key: 'base', label: '基本信息' },
                { key: 'profile', label: '用户画像' },
                { key: 'academics', label: '学业情况' },
                { key: 'requirements', label: '毕业要求达成' },
                { key: 'report', label: '学业报告' },
              ] as { key: ProfileTab; label: string }[]
            ).map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`px-4 py-2 rounded-full text-sm transition ${
                  activeTab === tab.key
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100/80 dark:bg-gray-800/80 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
                onClick={() => setSelectedTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'base' && (
            <div className="rounded-2xl panel panel-border p-6">
              <h2 className="text-lg font-semibold mb-4">个人信息</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                {infoRows.map((row) => (
                  <div key={row.label} className="flex items-center gap-3">
                    <span className="text-gray-500 dark:text-gray-400 w-20">{row.label}</span>
                    <span className="text-gray-700 dark:text-gray-200">{row.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'profile' && (
            <div className="rounded-2xl panel panel-border p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">用户画像</h2>
                <button
                  type="button"
                  onClick={handleGenerateProfile}
                  className="px-3 py-2 rounded-lg bg-emerald-500/20 text-emerald-100 hover:bg-emerald-500/30"
                >
                  生成画像
                </button>
              </div>
              <div className="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap">
                {publicProfile?.content || '暂无画像，请点击生成。'}
              </div>
              {status && <div className="text-xs text-gray-500 dark:text-gray-400">{status}</div>}
            </div>
          )}

          {activeTab === 'academics' && (
            <div className="rounded-2xl panel panel-border p-6">
              <h2 className="text-lg font-semibold mb-4">学业情况</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-gray-600 dark:text-gray-300">
                    <tr>
                      <th className="px-3 py-2 text-left">课程号</th>
                      <th className="px-3 py-2 text-left">课程名称</th>
                      <th className="px-3 py-2 text-left">任课教师</th>
                      <th className="px-3 py-2 text-left">成绩</th>
                      <th className="px-3 py-2 text-left">班级分位</th>
                      <th className="px-3 py-2 text-left">操作</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-700 dark:text-gray-200">
                    {courses.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-3 py-4 text-gray-500 dark:text-gray-400">
                          暂无课程数据
                        </td>
                      </tr>
                    ) : (
                      courses.map((course) => (
                        <tr
                          key={course.offering_id}
                          className="border-t border-gray-200/70 dark:border-gray-700/50"
                        >
                          <td className="px-3 py-2">{course.course_code}</td>
                          <td className="px-3 py-2">{course.course_name}</td>
                          <td className="px-3 py-2">{course.teacher_name || '-'}</td>
                          <td className="px-3 py-2">
                            {course.total_score ?? course.grade_text ?? '-'}
                          </td>
                          <td className="px-3 py-2">{formatPercentile(course.percentile)}</td>
                          <td className="px-3 py-2">
                            <button
                              type="button"
                              className="px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-100 hover:bg-blue-500/30"
                              onClick={() => navigate(`/profile/courses/${course.offering_id}`)}
                            >
                              查看课程目标达成
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'requirements' && (
            <div className="rounded-2xl panel panel-border p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">毕业要求达成</h2>
                <button
                  type="button"
                  onClick={handleRefreshRequirements}
                  className="px-3 py-2 rounded-lg bg-emerald-500/20 text-emerald-100 hover:bg-emerald-500/30"
                >
                  刷新数据
                </button>
              </div>
              {sortedGroupedRequirements.length ? (
                <div className="space-y-3">
                  {sortedGroupedRequirements.map((req) => {
                    const isExpanded = expandedRequirements[req.id] ?? false;
                    const children = req.children ?? [];
                    const hasChildren = children.length > 0;
                    return (
                      <div key={req.id} className="rounded-xl panel panel-border p-4">
                        <button
                          type="button"
                          className="w-full text-left flex items-start justify-between gap-4"
                          onClick={() => {
                            if (hasChildren) {
                              toggleRequirement(req.id);
                            }
                          }}
                        >
                          <div>
                            <div className="text-sm font-semibold">
                              {req.index || req.id} {req.description}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                              达成度：
                              {typeof req.achievement_rate === 'number'
                                ? req.achievement_rate.toFixed(2)
                                : '-'}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-xs px-2 py-1 rounded-full ${
                                req.achieved
                                  ? 'bg-emerald-500/20 text-emerald-100'
                                  : 'bg-amber-500/20 text-amber-100'
                              }`}
                            >
                              {req.achieved ? '已达成' : '待提升'}
                            </span>
                            {hasChildren && (
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {isExpanded ? '收起' : '展开'}
                              </span>
                            )}
                          </div>
                        </button>
                        {hasChildren && isExpanded && (
                          <div className="mt-3 space-y-2">
                            {children.map((child) => (
                              <div
                                key={child.id}
                                className="rounded-lg bg-gray-50 dark:bg-gray-900/40 border border-gray-200/60 dark:border-gray-700/50 p-3"
                              >
                                <div className="text-sm font-medium text-gray-700 dark:text-gray-200">
                                  {child.index || child.id} {child.description}
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                  达成度：
                                  {typeof child.achievement_rate === 'number'
                                    ? child.achievement_rate.toFixed(2)
                                    : '-'}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  暂无毕业要求达成数据
                </div>
              )}
              {status && <div className="text-xs text-gray-500 dark:text-gray-400">{status}</div>}
            </div>
          )}

          {activeTab === 'report' && (
            <div className="rounded-2xl panel panel-border p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">学业报告</h2>
                <button
                  type="button"
                  onClick={handleGenerateAcademicReport}
                  className="px-3 py-2 rounded-lg bg-emerald-500/20 text-emerald-100 hover:bg-emerald-500/30"
                >
                  生成报告
                </button>
              </div>
              <div className="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap">
                {academicReport?.content || '暂无报告，请点击生成。'}
              </div>
              {status && <div className="text-xs text-gray-500 dark:text-gray-400">{status}</div>}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
