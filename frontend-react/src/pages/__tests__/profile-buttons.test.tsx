import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { ProfilePage } from '../ProfilePage';

vi.mock('../../services/auth', () => ({
  authService: { getCurrentUser: () => Promise.resolve({ id: 1, username: 'demo' }) },
}));

vi.mock('../../services/profile', () => ({
  profileService: {
    getPublicProfile: () => Promise.resolve({ content: '' }),
    generatePublicProfile: () => Promise.resolve({ content: '' }),
    listAcademics: () =>
      Promise.resolve([
        {
          offering_id: 1,
          class_number: 'A1',
          course_name: '测试课程',
          percentile: 0.5,
        },
      ]),
    getGraduationRequirements: () =>
      Promise.resolve({
        data: {
          requirements_grouped: [
            { id: 1, description: 'req', achieved: false, children: [] },
          ],
        },
      }),
    refreshGraduationRequirements: () =>
      Promise.resolve({
        data: {
          requirements_grouped: [
            { id: 1, description: 'req', achieved: false, children: [] },
          ],
        },
      }),
    getAcademicReport: () => Promise.resolve({ content: '' }),
    generateAcademicReport: () => Promise.resolve({ content: '' }),
  },
}));

it('uses high-contrast button/badge classes in profile tabs', async () => {
  render(
    <MemoryRouter initialEntries={['/profile?tab=profile']}>
      <ProfilePage />
    </MemoryRouter>
  );

  const profileBtn = await screen.findByRole('button', { name: '生成画像' });
  expect(profileBtn).toHaveClass('btn-soft-success');

  fireEvent.click(screen.getByRole('button', { name: '学业情况' }));
  const courseBtn = await screen.findByRole('button', { name: '查看课程目标达成' });
  expect(courseBtn).toHaveClass('btn-soft-primary');

  fireEvent.click(screen.getByRole('button', { name: '毕业要求达成' }));
  const badge = await screen.findByText('待提升');
  expect(badge).toHaveClass('badge-warning');

  fireEvent.click(screen.getByRole('button', { name: '学业报告' }));
  const reportBtn = await screen.findByRole('button', { name: '生成报告' });
  expect(reportBtn).toHaveClass('btn-soft-success');
});
