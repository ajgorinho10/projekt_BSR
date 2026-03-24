import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';

import { useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';

import { Login } from './components/Login'
import { Register } from './components/Register';
import { Settings2FA } from './components/Settings';
import { AdminPanel } from './pages/AdminPanel';
import { SettingsPage } from './pages/SettingsPage';
import {DashboardPage} from "./pages/Dashboard.jsx";

import './App.css'; // Importujemy nasze nowe style

// Komponenty tymczasowe z klasami CSS
const Home = () => <div className="container"><h2>Strona Główna</h2><p>Dostępna dla każdego.</p></div>;
const Dashboard = () => <div className="container"><h2>Dashboard</h2><p>Witaj w swoim panelu.</p></div>;

function App() {
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <Router>
      <div className="app-wrapper">
        {/* Nowoczesna Nawigacja */}
        <nav className="navbar">
          <div className="nav-logo">
            <Link to="/">APP_LOGO</Link>
          </div>
          
          <div className="nav-links">
            {!isAuthenticated ? (
              <>
                <Link to="/login">Zaloguj</Link>
                <Link to="/register" className="nav-btn-primary">Zarejestruj</Link>
              </>
            ) : (
              <>
                <Link to="/dashboard">Panel</Link>
                <Link to="/settings">Ustawienia</Link>
                <Link to="/settings2FA">2FA</Link>
                
                {user?.role === 'admin' && (
                  <Link to="/admin" className="nav-admin-link">Admin</Link>
                )}
                
                <div className="nav-user-info">
                  <span>{user.username}</span>
                  <button onClick={logout} className="nav-logout-btn">Wyloguj</button>
                </div>
              </>
            )}
          </div>
        </nav>

        {/* Główny kontener na treści */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register/>}/>

            {/* Ścieżki chronione */}
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/settings" element={<SettingsPage/>}/>
              <Route path="/settings2FA" element={<Settings2FA/>}/>
            </Route>

            {/* Ścieżki Admina */}
            <Route element={<ProtectedRoute requireAdmin={true} />}>
              <Route path="/admin" element={<AdminPanel />} />
            </Route>
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;