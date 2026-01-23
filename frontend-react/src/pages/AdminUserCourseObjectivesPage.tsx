import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { adminService } from '../services/admin';
import type { UserCourse, UserCourseObjective, UserCourseReport } from '../types';

export function AdminUserCourseObjectivesPage() {
  const { userId, offeringId } = useParams();
  const [objectives, setObjectives] = useState<UserCourseObjective[]>([]);
  const [courseInfo, setCourseInfo] = useState<UserCourse | null>(null);
  const [report, setReport] = useState<UserCourseReport | null>(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!userId || !offeringId) return;
    const load = async () => {
      setStatus('加载中...');
      try {
        const [courses, objectivesData] = await Promise.all([
          adminService.listUserAcademics(Number(userId)),
          adminService.listUserCourseObjectives(Number(userId), Number(offeringId)),
        ]);
        setCourseInfo(courses.find((item) => item.offering_id === Number(offeringId)) || null);
        setObjectives(objectivesData);
        setStatus('');
      } catch (error) {
        setStatus(error instanceof Error ? error.message : '加载失败');
      }
    };
    load();
  }, [userId, offeringId]);

  const handleLoadReport = async () => {
    if (!userId || !offeringId) return;
    setStatus('加载报告中...');
    try {
      const data = await adminService.getUserCourseReport(Number(userId), Number(offeringId));
      setReport(data);
      setStatus('');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '加载失败');
    }
  };

  const formatPercentile = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    return `${(value * 100).toFixed(1)}%`;
  };

  return (
    <Layout title="课程目标达成">
      <div className="min-h-[calc(100vh-4rem)] bg-slate-950 text-slate-100">
        <div className="container mx-auto px-4 py-8 space-y-6">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h2 className="text-lg font-semibold">课程目标达成情况</h2>
            <p className="text-sm text-slate-300 mt-2">
              {courseInfo
                ? `${courseInfo.course_code} · ${courseInfo.course_name}`
                : `课程 ${offeringId}`}
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            {status ? (
              <div className="text-sm text-slate-300">{status}</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-slate-300">
                    <tr>
                      <th className="px-3 py-2 text-left">目标序号</th>
                      <th className="px-3 py-2 text-left">目标描述</th>
                      <th className="px-3 py-2 text-left">达成度</th>
                      <th className="px-3 py-2 text-left">班级分位</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-200">
                    {objectives.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-3 py-4 text-slate-400">
                          暂无课程目标数据
                        </td>
                      </tr>
                    ) : (
                      objectives.map((objective) => (
                        <tr key={objective.objective_id} className="border-t border-white/5">
                          <td className="px-3 py-2">{objective.objective_index || objective.objective_id}</td>
                          <td className="px-3 py-2">{objective.description}</td>
                          <td className="px-3 py-2">
                            {objective.achievement_score ?? '-'}
                          </td>
                          <td className="px-3 py-2">{formatPercentile(objective.percentile)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">课程目标达成报告</h3>
              <button
                type="button"
                className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-100 hover:bg-emerald-500/30"
                onClick={handleLoadReport}
              >
                显示报告
              </button>
            </div>
            <div className="text-sm text-slate-200 whitespace-pre-wrap">
              {report?.content || '暂无报告，请在学生端生成后查看。'}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
