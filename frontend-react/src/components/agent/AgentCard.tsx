import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { MessageSquare, ChevronRight } from 'lucide-react';
import type { AgentConfig } from '../../types';

interface AgentCardProps {
  config: AgentConfig;
  index: number;
}

export function AgentCard({ config, index }: AgentCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="group relative"
    >
      <Link to={`/chat/${config.type}`}>
        <div
          className="relative h-64 rounded-2xl overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-2"
          style={{
            backgroundImage: `linear-gradient(135deg, ${config.color}40 0%, ${config.colorDark}60 100%)`,
          }}
        >
          {/* Background image with overlay */}
          <div
            className="absolute inset-0 bg-cover bg-center opacity-30 group-hover:opacity-40 transition-opacity"
            style={{ backgroundImage: `url(${config.backgroundImage})` }}
          />

          {/* Gradient overlay */}
          <div
            className="absolute inset-0"
            style={{
              background: `linear-gradient(180deg, transparent 0%, ${config.colorDark}90 100%)`,
            }}
          />

          {/* Glow effect on hover */}
          <div
            className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
            style={{
              boxShadow: `inset 0 0 60px ${config.color}40`,
            }}
          />

          {/* Content */}
          <div className="absolute inset-0 p-6 flex flex-col justify-end">
            {/* Icon */}
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 backdrop-blur-sm"
              style={{ backgroundColor: `${config.color}30` }}
            >
              <MessageSquare size={24} className="text-white" />
            </div>

            {/* Title */}
            <h3 className="text-2xl font-bold text-white mb-2 group-hover:translate-x-1 transition-transform">
              {config.titleZh}
            </h3>

            {/* Description */}
            <p className="text-white/80 text-sm line-clamp-2 mb-4">
              {config.description}
            </p>

            {/* Action */}
            <div className="flex items-center text-white/90 text-sm font-medium group-hover:translate-x-2 transition-transform">
              <span>开始对话</span>
              <ChevronRight size={18} className="ml-1" />
            </div>
          </div>

          {/* Decorative elements */}
          <div
            className="absolute top-4 right-4 w-20 h-20 rounded-full opacity-20 blur-xl group-hover:scale-150 transition-transform duration-700"
            style={{ backgroundColor: config.color }}
          />
        </div>
      </Link>
    </motion.div>
  );
}
