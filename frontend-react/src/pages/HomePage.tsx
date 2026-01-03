import { motion } from 'framer-motion';
import { Layout } from '../components/layout/Layout';
import { AgentCard } from '../components/agent/AgentCard';
import { AGENT_LIST, AGENT_CONFIGS } from '../utils/constants';
import { Sparkles } from 'lucide-react';

export function HomePage() {
  return (
    <Layout>
      {/* Hero section */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 py-16 sm:py-24">
        {/* Animated background elements */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse-slow" />
          <div className="absolute top-40 -left-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse-slow" />
          <div className="absolute -bottom-40 left-1/2 w-80 h-80 bg-cyan-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse-slow" />
        </div>

        <div className="container mx-auto px-4 relative">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full text-sm text-blue-200 mb-6">
              <Sparkles size={16} />
              <span>AI 驱动的智能教育平台</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-6">
              AutoChat
              <span className="block text-2xl sm:text-3xl lg:text-4xl font-normal text-blue-200 mt-2">
                智能教育对话系统
              </span>
            </h1>

            <p className="text-lg text-gray-300 max-w-2xl mx-auto mb-8">
              六大专业智能体，为您提供个性化的教育辅导服务。
              从思政教育到学科竞赛，全方位助力您的学习之旅。
            </p>
          </motion.div>
        </div>
      </div>

      {/* Agents grid */}
      <div className="container mx-auto px-4 py-12 sm:py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-center mb-12"
        >
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-4">
            选择您的智能助手
          </h2>
          <p className="text-gray-600 dark:text-gray-400 max-w-xl mx-auto">
            每个智能体都经过专业训练，能够为您提供特定领域的专业指导
          </p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {AGENT_LIST.map((agentType, index) => (
            <AgentCard
              key={agentType}
              config={AGENT_CONFIGS[agentType]}
              index={index}
            />
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-100 dark:bg-gray-800 py-8 border-t border-gray-200 dark:border-gray-700">
        <div className="container mx-auto px-4 text-center">
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            © 2024 AutoChat. 基于先进的大语言模型技术构建。
          </p>
        </div>
      </footer>
    </Layout>
  );
}
