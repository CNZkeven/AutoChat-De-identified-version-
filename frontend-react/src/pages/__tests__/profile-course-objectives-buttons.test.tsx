import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { ProfileCourseObjectivesPage } from '../ProfileCourseObjectivesPage';

vi.mock('../../services/profile', () => ({
  profileService: {
    listCourseObjectives: () => Promise.resolve([]),
    getCourseReport: () => Promise.resolve({ content: '' }),
    generateCourseReport: () => Promise.resolve({ content: '' }),
  },
}));

it('uses high-contrast buttons in course objectives page', async () => {
  render(
    <MemoryRouter initialEntries={['/profile/courses/1']}>
      <Routes>
        <Route path="/profile/courses/:offeringId" element={<ProfileCourseObjectivesPage />} />
      </Routes>
    </MemoryRouter>
  );

  const reportBtn = await screen.findByRole('button', { name: '生成报告' });
  expect(reportBtn).toHaveClass('btn-soft-success');
});
