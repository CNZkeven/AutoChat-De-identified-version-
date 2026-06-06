import { describe, expect, it } from 'vitest';
import { normalizeAssistantMarkdown } from '../markdownContent';

describe('normalizeAssistantMarkdown', () => {
  it('converts HTML br tags from model output into markdown line breaks', () => {
    expect(normalizeAssistantMarkdown('准备材料<br>前置条件<br/>复习资料<BR />错题本')).toBe(
      '准备材料\n前置条件\n复习资料\n错题本'
    );
  });

  it('leaves normal markdown unchanged', () => {
    const markdown = '1. 任务拆解\n\n| 步骤 | 优先级 |\n| --- | --- |';

    expect(normalizeAssistantMarkdown(markdown)).toBe(markdown);
  });
});
