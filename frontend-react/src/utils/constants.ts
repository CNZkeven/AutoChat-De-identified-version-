import type { AgentConfig, AgentType } from '../types';

export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const AGENT_CONFIGS: Record<AgentType, AgentConfig> = {
  ideological: {
    type: 'ideological',
    title: 'Ideological Agent',
    titleZh: '思政智能体',
    description: '提供思想政治教育指导，帮助理解和践行社会主义核心价值观',
    color: '#ff6b6b',
    colorDark: '#e85555',
    colorLight: '#ff8787',
    backgroundImage: '/images/4e95f6fa4fbda42e8482ba06506284ce_0.jpg',
    greeting: '你好！我是思政智能体，可以帮助你了解思想政治教育相关内容。',
  },
  evaluation: {
    type: 'evaluation',
    title: 'Evaluation Agent',
    titleZh: '评价智能体',
    description: '提供学习评价和反馈，帮助改进学习方法和效果',
    color: '#48dbfb',
    colorDark: '#22c7e5',
    colorLight: '#6fe3fc',
    backgroundImage: '/images/3abee1adc3279109c8ede1004eba52c8_0.jpg',
    greeting: '你好！我是评价智能体，可以帮助你评估学习进度和效果。',
  },
  task: {
    type: 'task',
    title: 'Task Agent',
    titleZh: '任务智能体',
    description: '提供任务规划和执行指导，帮助高效完成学习任务',
    color: '#1dd1a1',
    colorDark: '#15b88a',
    colorLight: '#45d9b3',
    backgroundImage: '/images/dff83e09cf9a55b16ba337ed1c51e1a8_0.jpg',
    greeting: '你好！我是任务智能体，可以帮助你规划和完成学习任务。',
  },
  exploration: {
    type: 'exploration',
    title: 'Exploration Agent',
    titleZh: '探究智能体',
    description: '引导探究式学习，培养独立思考和研究能力',
    color: '#feca57',
    colorDark: '#e5b343',
    colorLight: '#fed674',
    backgroundImage: '/images/1f70d339b0b9eda3f95387bc102b4644_0.jpg',
    greeting: '你好！我是探究智能体，可以帮助你进行探究式学习。',
  },
  competition: {
    type: 'competition',
    title: 'Competition Agent',
    titleZh: '竞赛智能体',
    description: '提供竞赛准备指导，帮助在各类学科竞赛中取得好成绩',
    color: '#5f27cd',
    colorDark: '#4a1fa8',
    colorLight: '#7b4dd4',
    backgroundImage: '/images/eaacf4c0a0bdadbdb1cadbf40773ce48.jpg',
    greeting: '你好！我是竞赛智能体，可以帮助你准备各类学科竞赛。',
  },
  course: {
    type: 'course',
    title: 'Course Agent',
    titleZh: '课程智能体',
    description: '提供课程学习辅导，帮助理解和掌握课程内容',
    color: '#ff9ff3',
    colorDark: '#e580d9',
    colorLight: '#ffb8f6',
    backgroundImage: '/images/a43168df1330ad63a3cb3f63563bb2d8_720.jpg',
    greeting: '你好！我是课程智能体，可以帮助你学习课程内容。',
  },
};

export const AGENT_LIST: AgentType[] = [
  'ideological',
  'evaluation',
  'task',
  'exploration',
  'competition',
  'course',
];

export const getAgentConfig = (agent: string): AgentConfig | undefined => {
  return AGENT_CONFIGS[agent as AgentType];
};
