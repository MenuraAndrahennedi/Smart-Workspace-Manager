import { NavLink, Outlet } from "react-router-dom";
import useAuth from "../context/useAuth";
import "./AppLayout.css";

function AppLayout() {
  const { currentUser, logout } = useAuth();

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">SW</span>
          <div><p className="brand-name">Smart Workspace</p><p className="brand-subtitle">Manager</p></div>
        </div>

        <nav className="nav-menu" aria-label="Main navigation">
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/upload">Upload</NavLink>
          <NavLink to="/library">Library</NavLink>
          <NavLink to="/xlsx-to-csv">XLSX to CSV</NavLink>
          <NavLink to="/analyzer">Analyzer</NavLink>
          <NavLink to="/cleaning">Cleaning</NavLink>
          <NavLink to="/reports">Reports</NavLink>
        </nav>

        <div className="sidebar-user">
          <p className="sidebar-label">Signed in as</p>
          <p className="sidebar-email">{currentUser?.email}</p>
          <button className="logout-button" type="button" onClick={logout}>Sign out</button>
        </div>
      </aside>

      <main className="main-content"><Outlet /></main>
    </div>
  );
}

export default AppLayout;
