import type { Message } from '../types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasToolCallShape(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.some(hasToolCallShape);
  }
  if (!isRecord(value)) {
    return false;
  }
  if ('tool' in value && 'args' in value) {
    return true;
  }
  if (Array.isArray(value.tool_calls) && value.tool_calls.some(hasToolCallShape)) {
    return true;
  }
  if (isRecord(value.function) && 'name' in value.function && 'arguments' in value.function) {
    return true;
  }
  return 'name' in value && 'arguments' in value;
}

export function looksLikeToolCallLeak(content: string | null | undefined): boolean {
  const trimmed = content?.trim();
  if (!trimmed) {
    return false;
  }
  if (trimmed.includes('<tool_call>') || trimmed.includes('</tool_call>')) {
    return true;
  }
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
    return false;
  }
  if (!/"(?:tool|tool_calls|args|arguments)"\s*:/.test(trimmed)) {
    return false;
  }
  try {
    return hasToolCallShape(JSON.parse(trimmed));
  } catch {
    return /"tool"\s*:/.test(trimmed) && /"args"\s*:/.test(trimmed);
  }
}

export function removeToolCallLeakMessages(messages: Message[]): Message[] {
  return messages.filter((message) => !(message.role === 'assistant' && looksLikeToolCallLeak(message.content)));
}
