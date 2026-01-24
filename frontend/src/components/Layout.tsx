import type { ReactNode } from 'react';
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Menu } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const menuItems = [
    { text: 'Log Session', path: '/log-session' },
    { text: 'Sessions', path: '/sessions' },
    { text: 'Projects', path: '/projects' },
  ];

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside
        className={cn(
          'border-r bg-background transition-all duration-300 ease-in-out',
          sidebarOpen ? 'w-64' : 'w-0'
        )}
      >
        <div className={cn('h-full', sidebarOpen ? 'block' : 'hidden')}>
          <div className="border-b p-4">
            <h1 className="text-xl font-semibold">Measured</h1>
          </div>
          <nav className="p-2">
            {menuItems.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={cn(
                  'w-full text-left px-4 py-3 rounded-md transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  location.pathname === item.path &&
                    'bg-accent text-accent-foreground font-medium'
                )}
              >
                {item.text}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col">
        <header className="border-b p-4 flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <span className="text-sm text-muted-foreground">
            {sidebarOpen ? 'Hide' : 'Show'} sidebar
          </span>
        </header>
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

