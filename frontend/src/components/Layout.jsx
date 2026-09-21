import { NavLink, Outlet } from "react-router-dom";
import { Menu, X, LayoutGrid, Upload, BarChart3 } from "lucide-react";
import { useState } from "react";
import IconBadge from "./IconBadge";

const navItems = [
  { to: "/", label: "Datasets", icon: LayoutGrid, end: true },
  { to: "/upload", label: "Upload", icon: Upload },
];

function NavItem({ to, label, icon: Icon, end, onClick }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? "bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300"
            : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        }`
      }
    >
      <Icon className="h-4.5 w-4.5" strokeWidth={2} />
      {label}
    </NavLink>
  );
}

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      {/* Mobile top bar */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 md:hidden">
        <div className="flex items-center gap-2.5">
          <IconBadge icon={BarChart3} size="sm" />
          <span className="font-semibold text-slate-900 dark:text-white">
            AI Data Analyst
          </span>
        </div>
        <button
          onClick={() => setMobileOpen((v) => !v)}
          className="rounded-md p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          aria-label="Toggle navigation"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      <div className="mx-auto flex max-w-7xl">
        {/* Sidebar: hidden on mobile unless toggled, always visible on md+ */}
        <aside
          className={`${
            mobileOpen ? "block" : "hidden"
          } w-full border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 md:sticky md:top-0 md:block md:h-screen md:w-64 md:shrink-0 md:border-b-0 md:border-r`}
        >
          <div className="hidden items-center gap-3 px-6 py-5 md:flex">
            <IconBadge icon={BarChart3} size="md" />
            <span className="text-lg font-semibold text-slate-900 dark:text-white">
              AI Data Analyst
            </span>
          </div>
          <nav className="space-y-1 p-4">
            {navItems.map((item) => (
              <NavItem key={item.to} {...item} onClick={() => setMobileOpen(false)} />
            ))}
          </nav>
        </aside>

        {/* Main content */}
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
