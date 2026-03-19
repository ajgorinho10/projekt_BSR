import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';

import { useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';

import {Login} from './components/Login'
import { Register } from './components/Register';
import { Settings2FA } from './components/Settings';

// Tymczasowe komponenty (Zaraz zamienimy je na prawdziwe pliki!)
const Home = () => <h2>Strona Główna (Dostępna dla każdego)</h2>;
const Dashboard = () => <h2>Panel Użytkownika (Tylko dla zalogowanych)</h2>;
const AdminPanel = () => <h2>Tajny Panel Admina (Tylko dla Adminów)</h2>;

function App() {
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <Router>
      <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
        {/* Prosta Nawigacja */}
        <nav style={{ marginBottom: '20px', borderBottom: '1px solid #ccc', paddingBottom: '10px' }}>
          
          {!isAuthenticated ? (
            <>
            <Link to="/login" style={{ marginRight: '10px' }}>Zaloguj</Link>
            <Link to="/register" style={{ marginRight: '10px' }}>Zarejestruj</Link>
            </>
          ) : (
            <>
              <Link to="/dashboard" style={{ marginRight: '10px' }}>Mój Panel</Link>
              <Link to="/settings2FA" style={{ marginRight: '10px' }}>Ustaw 2FA</Link>
              {user?.role === 'admin' && (
                <Link to="/admin" style={{ marginRight: '10px', color: 'red' }}>Panel Admina</Link>
              )}
              <button onClick={logout} style={{ marginLeft: '10px' }}>Wyloguj ({user.username})</button>
            </>
          )}
        </nav>

        {/* Definicja Ścieżek (Routing) */}
        <Routes>
          {/* Strony publiczne */}
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register/>}/>

          {/* Strony CHRONIONE (Tylko dla zalogowanych) */}
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/settings2FA" element={<Settings2FA/>}/>
          </Route>

          {/* Strony CHRONIONE (Tylko dla Admina) */}
          <Route element={<ProtectedRoute requireAdmin={true} />}>
            <Route path="/admin" element={<AdminPanel />} />
          </Route>
        </Routes>
      </div>
    </Router>
  );
}

export default App;