import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { adminService } from '../services/admin';
import type { AdminUser, UserCourse } from '../types';

export function AdminUserAcademicsPage() {
  const { userId } = useParams();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [courses, setCourses] = useState<UserCourse[]>([]);
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!userId) return;
    const load = async () => {
      setStatus('加载中...');
      try {
        const [userInfo, courseData] = await Promise.all([
          adminService.getUser(Number(userId)),
          adminService.listUserAcademics(Number(userId)),
        ]);
        setUser(userInfo);
        setCourses(courseData);
        setStatus('');
      } catch (error) {
        setStatus(error instanceof Error ? error.message : '加载失败');
      }
    };
    load();
  }, [userId]);

  const formatPercentile = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    return `${(value * 100).toFixed(1)}%`;
  };

  return (
    <Layout title="学业情况">
      <div className="min-h-[calc(100vh-4rem)] bg-slate-950 text-slate-100">
        <div className="container mx-auto px-4 py-8 space-y-6">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h2 className="text-lg font-semibold">学业情况</h2>
            <p className="text-sm text-slate-300 mt-2">
              {user?.full_name || user?.username || '未知用户'}
              {user?.major ? ` · ${user.major}` : ''}
              {user?.grade ? ` · ${user.grade}级` : ''}
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
                      <th className="px-3 py-2 text-left">课程号</th>
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
                              onClick={() =>
                                window.open(
                                  `/admin/users/${userId}/courses/${course.offering_id}/objectives`,
                                  '_blank'
                                )
                              }
                            >
                              查看课程目标达成报告
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
