import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { profileService } from '../services/profile';
import type { UserCourseObjective, UserCourseReport } from '../types';

export function ProfileCourseObjectivesPage() {
  const { offeringId } = useParams();
  const navigate = useNavigate();
  const [objectives, setObjectives] = useState<UserCourseObjective[]>([]);
  const [report, setReport] = useState<UserCourseReport | null>(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!offeringId) return;
    const load = async () => {
      setStatus('加载中...');
      try {
        const [objectiveData, reportData] = await Promise.all([
          profileService.listCourseObjectives(Number(offeringId)),
          profileService.getCourseReport(Number(offeringId)),
        ]);
        setObjectives(objectiveData);
        setReport(reportData);
        setStatus('');
      } catch (error) {
        setStatus(error instanceof Error ? error.message : '加载失败');
      }
    };
    load();
  }, [offeringId]);

  const handleGenerateReport = async () => {
    if (!offeringId) return;
    setStatus('生成报告中...');
    try {
      const data = await profileService.generateCourseReport(Number(offeringId));
      setReport(data);
      setStatus('生成完成');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '生成失败');
    }
  };

  const formatPercentile = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    return `${(value * 100).toFixed(1)}%`;
  };

  return (
    <Layout title="课程目标达成">
      <div className="min-h-[calc(100vh-4rem)]">
        <div className="container mx-auto px-4 py-8 space-y-6">
          <div className="rounded-2xl panel panel-border p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">课程目标达成情况</h2>
                <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">
                  课程 ID：{offeringId}
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate('/profile?tab=academics')}
                className="px-3 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
              >
                返回学业情况
              </button>
            </div>
          </div>

          <div className="rounded-2xl panel panel-border p-6">
            {status ? (
              <div className="text-sm text-gray-600 dark:text-gray-300">{status}</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-gray-600 dark:text-gray-300">
                    <tr>
                      <th className="px-3 py-2 text-left">目标序号</th>
                      <th className="px-3 py-2 text-left">目标描述</th>
                      <th className="px-3 py-2 text-left">达成度</th>
                      <th className="px-3 py-2 text-left">班级分位</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-700 dark:text-gray-200">
                    {objectives.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-3 py-4 text-gray-500 dark:text-gray-400">
                          暂无课程目标数据
                        </td>
                      </tr>
                    ) : (
                      objectives.map((objective) => (
                        <tr
                          key={objective.objective_id}
                          className="border-t border-gray-200/70 dark:border-gray-700/50"
                        >
                          <td className="px-3 py-2">{objective.objective_index || objective.objective_id}</td>
                          <td className="px-3 py-2">{objective.description}</td>
                          <td className="px-3 py-2">{objective.achievement_score ?? '-'}</td>
                          <td className="px-3 py-2">{formatPercentile(objective.percentile)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="rounded-2xl panel panel-border p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">课程目标达成报告</h3>
              <button
                type="button"
                onClick={handleGenerateReport}
                className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-100 hover:bg-emerald-500/30"
              >
                生成报告
              </button>
            </div>
            <div className="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap">
              {report?.content || '暂无报告，请点击生成。'}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
