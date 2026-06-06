export function normalizeAssistantMarkdown(content: string): string {
  return content.replace(/<br\s*\/?>/gi, '\n');
}
