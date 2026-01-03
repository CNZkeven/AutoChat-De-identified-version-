import { Navbar } from './Navbar';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  agentColor?: string;
  showNavbar?: boolean;
}

export function Layout({ children, title, agentColor, showNavbar = true }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {showNavbar && <Navbar title={title} agentColor={agentColor} />}
      {children}
    </div>
  );
}
