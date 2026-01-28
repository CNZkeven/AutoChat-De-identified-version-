import { Link, useNavigate } from 'react-router-dom';
import { Home, LogOut, Moon, Sun, User, Shield } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useUIStore } from '../../store/uiStore';

interface NavbarProps {
  title?: string;
  agentColor?: string;
}

export function Navbar({ title, agentColor }: NavbarProps) {
  const { isAuthenticated, user, logout } = useAuthStore();
  const { darkMode, toggleDarkMode } = useUIStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav
      className="sticky top-0 z-50 glass border-b border-white/10"
      style={agentColor ? { borderBottomColor: agentColor } : undefined}
    >
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Title */}
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="flex items-center gap-2 text-gray-800 dark:text-white hover:text-primary-500 transition-colors"
            >
              <Home size={24} />
              <span className="font-bold text-xl hidden sm:inline">AutoChat</span>
            </Link>

            {title && (
              <>
                <span className="text-gray-400">/</span>
                <h1
                  className="font-semibold text-lg"
                  style={agentColor ? { color: agentColor } : undefined}
                >
                  {title}
                </h1>
              </>
            )}
          </div>

          {/* Right side actions */}
          <div className="flex items-center gap-3">
            {/* Dark mode toggle */}
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              aria-label="Toggle dark mode"
            >
              {darkMode ? (
                <Sun size={20} className="text-yellow-500" />
              ) : (
                <Moon size={20} className="text-gray-600" />
              )}
            </button>

            {isAuthenticated ? (
              <>
                {/* User info */}
                <Link
                  to="/profile"
                  className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                >
                  <User size={16} className="text-gray-500" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {user?.full_name || user?.username}
                  </span>
                </Link>

                {user?.username === 'admin' && (
                  <Link
                    to="/admin"
                    className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 text-blue-500 dark:text-blue-300 rounded-lg hover:bg-blue-500/20 transition-colors"
                  >
                    <Shield size={16} />
                    <span className="text-sm font-medium">管理员</span>
                  </Link>
                )}

                {/* Logout button */}
                <button
                  onClick={handleLogout}
                  className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-600 dark:text-gray-400 hover:text-red-500 transition-colors"
                  aria-label="Logout"
                >
                  <LogOut size={20} />
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium"
              >
                登录
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
