import type { ReactNode } from 'react';
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Menu, X, Clock, List, Folder } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LayoutProps {
  children: ReactNode;
}

const checkIsMobile = () => window.innerWidth < 768;

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  // Single state: mobile (true=visible, false=hidden), desktop (true=expanded, false=collapsed)
  // Initialize mobile detection synchronously to avoid flash on mobile
  const [isMobile, setIsMobile] = useState(checkIsMobile());
  const [sidebarOpen, setSidebarOpen] = useState(!checkIsMobile());

  // Handle window resize to update mobile/desktop state
  useEffect(() => {
    const handleResize = () => {
      const mobile = checkIsMobile();
      setIsMobile(mobile);
      // Update sidebar state when switching between mobile and desktop
      setSidebarOpen(!mobile);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const menuItems = [
    { text: 'Log\u00A0Session', path: '/log-session', icon: Clock },
    { text: 'Sessions', path: '/sessions', icon: List },
    { text: 'Projects', path: '/projects', icon: Folder },
  ];

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="flex min-h-screen">
      {/* Mobile backdrop */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'bg-background transition-all duration-300 ease-in-out border-r',
          // Mobile: overlay with fixed position
          isMobile && 'fixed left-0 top-0 h-full z-50',
          isMobile && (sidebarOpen ? 'translate-x-0' : '-translate-x-full'),
          isMobile && 'w-4/5 max-w-sm',
          // Desktop: push content
          !isMobile && 'relative',
          !isMobile && (sidebarOpen ? 'w-64' : 'w-16')
        )}
      >
        <div className="h-full flex flex-col">
          {/* Header area */}
          <div
            className={cn(
              'border-b px-4 py-2.5 flex items-center',
              isMobile ? 'justify-end' : 'justify-start'
            )}
          >
            {isMobile ? (
              // Close button on mobile
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(false)}
              >
                <X className="h-5 w-5" />
              </Button>
            ) : (
              // Toggle button on desktop
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
              >
                <Menu className="h-5 w-5" />
              </Button>
            )}
          </div>
          <nav className="p-2 flex-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.path}
                  onClick={() => {
                    navigate(item.path);
                    if (isMobile) setSidebarOpen(false);
                  }}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-md transition-colors',
                    'hover:bg-accent hover:text-accent-foreground',
                    location.pathname === item.path &&
                      'bg-accent text-accent-foreground font-medium',
                    !sidebarOpen && !isMobile && 'justify-center px-2'
                  )}
                  title={!sidebarOpen && !isMobile ? item.text : undefined}
                >
                  <Icon className="h-5 w-5 flex-shrink-0" />
                  <span
                    className={cn(
                      'transition-opacity',
                      !sidebarOpen && !isMobile && 'hidden'
                    )}
                  >
                    {item.text}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col">
        <header
          className={cn(
            'border-b flex items-center gap-3',
            isMobile ? 'px-4 py-2.5' : 'p-4'
          )}
        >
          {/* Hamburger only on mobile */}
          {isMobile && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
            >
              <Menu className="h-5 w-5" />
            </Button>
          )}
          <h1 className="text-xl font-semibold">Measured</h1>
        </header>
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

