import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
};

export function ProfilePage() {
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<ProfileTab>('base');
  const [publicProfile, setPublicProfile] = useState<UserProfile | null>(null);
  const [courses, setCourses] = useState<UserCourse[]>([]);
  const [requirements, setRequirements] = useState<UserGraduationRequirement | null>(null);
  const [academicReport, setAcademicReport] = useState<UserAcademicReport | null>(null);
  const [status, setStatus] = useState('');

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

  const requirementItems = useMemo(() => {
    const raw = (requirements?.data as { requirements?: unknown[] } | undefined)?.requirements || [];
    return raw as RequirementItem[];
  }, [requirements]);

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

  return (
    <Layout title="个人中心">
      <div className="min-h-[calc(100vh-4rem)] bg-slate-950 text-slate-100">
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
                    ? 'bg-blue-500 text-white'
                    : 'bg-white/10 text-slate-200 hover:bg-white/20'
                }`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'base' && (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <h2 className="text-lg font-semibold mb-4">个人信息</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                {infoRows.map((row) => (
                  <div key={row.label} className="flex items-center gap-3">
                    <span className="text-slate-400 w-20">{row.label}</span>
                    <span className="text-slate-200">{row.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'profile' && (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 space-y-4">
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
              <div className="text-sm text-slate-200 whitespace-pre-wrap">
                {publicProfile?.content || '暂无画像，请点击生成。'}
              </div>
              {status && <div className="text-xs text-slate-400">{status}</div>}
            </div>
          )}

          {activeTab === 'academics' && (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
              <h2 className="text-lg font-semibold mb-4">学业情况</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-slate-300">
                    <tr>
                      <th className="px-3 py-2 text-left">教学班号</th>
                      <th className="px-3 py-2 text-left">课程名称</th>
                      <th className="px-3 py-2 text-left">任课教师</th>
                      <th className="px-3 py-2 text-left">成绩</th>
                      <th className="px-3 py-2 text-left">班级分位</th>
                      <th className="px-3 py-2 text-left">操作</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-200">
                    {courses.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-3 py-4 text-slate-400">
                          暂无课程数据
                        </td>
                      </tr>
                    ) : (
                      courses.map((course) => (
                        <tr key={course.offering_id} className="border-t border-white/5">
                          <td className="px-3 py-2">{course.class_number || course.course_code}</td>
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
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 space-y-4">
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
              {requirementItems.length ? (
                <div className="grid gap-3">
                  {requirementItems.map((req) => (
                    <div
                      key={req.id}
                      className="rounded-xl border border-white/10 bg-slate-900/60 p-4"
                    >
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-semibold text-slate-100">
                          {req.index || req.id} {req.description}
                        </div>
                        <span
                          className={`text-xs px-2 py-1 rounded-full ${
                            req.achieved ? 'bg-emerald-500/20 text-emerald-100' : 'bg-amber-500/20 text-amber-100'
                          }`}
                        >
                          {req.achieved ? '已达成' : '待提升'}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 mt-2">
                        达成度：
                        {typeof req.achievement_rate === 'number'
                          ? req.achievement_rate.toFixed(2)
                          : '-'}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-slate-400">暂无毕业要求达成数据</div>
              )}
              {status && <div className="text-xs text-slate-400">{status}</div>}
            </div>
          )}

          {activeTab === 'report' && (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 space-y-4">
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
              <div className="text-sm text-slate-200 whitespace-pre-wrap">
                {academicReport?.content || '暂无报告，请点击生成。'}
              </div>
              {status && <div className="text-xs text-slate-400">{status}</div>}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
