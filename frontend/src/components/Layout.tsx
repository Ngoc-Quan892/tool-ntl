import { ReactNode } from "react";
import { useUIStore } from "../stores";
import { Menu, X, BarChart3, Settings, Home } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface LayoutProps {
  children: ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  const { sidebarOpen, toggleSidebar, activeTab, setActiveTab } = useUIStore();

  const navItems = [
    { id: "prediction", label: "Prediction", icon: Home },
    { id: "statistics", label: "Statistics", icon: BarChart3 },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-casino-bg text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-casino-card/95 backdrop-blur-sm border-b border-casino-border">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={toggleSidebar}
                className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
                aria-label="Toggle sidebar"
              >
                {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
              <div>
                <h1 className="text-2xl font-black tracking-wide">🎰 Baccarat Predictor Pro</h1>
                <p className="text-sm text-slate-400">Card counting + ML + casino roadmaps</p>
              </div>
            </div>
            <nav className="hidden md:flex gap-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                      activeTab === item.id
                        ? "bg-casino-gold text-black"
                        : "hover:bg-slate-800"
                    }`}
                  >
                    <Icon size={18} />
                    {item.label}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.aside
              initial={{ x: -300, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -300, opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed md:static inset-y-0 left-0 z-40 w-64 bg-casino-card border-r border-casino-border"
            >
              <div className="h-full overflow-y-auto p-4">
                <nav className="space-y-2">
                  {navItems.map((item) => {
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          setActiveTab(item.id);
                          if (window.innerWidth < 768) {
                            toggleSidebar();
                          }
                        }}
                        className={`w-full px-4 py-3 rounded-lg transition-colors flex items-center gap-3 ${
                          activeTab === item.id
                            ? "bg-casino-gold text-black font-semibold"
                            : "hover:bg-slate-800"
                        }`}
                      >
                        <Icon size={20} />
                        {item.label}
                      </button>
                    );
                  })}
                </nav>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Overlay for mobile */}
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={toggleSidebar}
            className="fixed inset-0 bg-black/50 z-30 md:hidden"
          />
        )}

        {/* Main content */}
        <main className="flex-1 container mx-auto px-4 py-6 md:px-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;

