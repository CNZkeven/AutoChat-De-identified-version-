import { describe, expect, it } from 'vitest';
import { looksLikeToolCallLeak, removeToolCallLeakMessages } from '../toolCallGuard';
import type { Message } from '../../types';

describe('toolCallGuard', () => {
  it('detects a plain tool-call JSON message', () => {
    expect(
      looksLikeToolCallLeak('{"tool": "get_user_comprehensive_profile", "args": {"user_id": 2, "scope": "basic"}}')
    ).toBe(true);
  });

  it('does not flag ordinary assistant text', () => {
    expect(looksLikeToolCallLeak('可以从制度建设、课程案例和船舶工程实践三个层面融入。')).toBe(false);
  });

  it('removes only leaked assistant messages from history', () => {
    const messages: Message[] = [
      {
        id: 1,
        role: 'user',
        content: '如何将新时代党建教育融入到船舶中',
        created_at: '2026-06-06T16:01:00.000Z',
      },
      {
        id: 2,
        role: 'assistant',
        content: '{"tool": "get_user_comprehensive_profile", "args": {"user_id": 2, "scope": "basic"}}',
        created_at: '2026-06-06T16:01:01.000Z',
      },
      {
        id: 3,
        role: 'assistant',
        content: '可以从制度建设、课程案例和船舶工程实践三个层面融入。',
        created_at: '2026-06-06T16:01:02.000Z',
      },
    ];

    expect(removeToolCallLeakMessages(messages).map((message) => message.id)).toEqual([1, 3]);
  });
});
