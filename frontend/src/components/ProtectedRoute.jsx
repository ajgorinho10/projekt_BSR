import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

import { NodesProvider } from '../context/NodesContext';

export const ProtectedRoute = ({ requireAdmin = false }) => {
    const { isAuthenticated, isAdmin, isLoading } = useAuth();

    // Jeśli aplikacja wciąż sprawdza tokeny w tle, nie pokazujemy nic
    if (isLoading) {
        return <div style={{ textAlign: 'center', marginTop: '50px' }}>Sprawdzanie uprawnień...</div>;
    }

    // Jeśli użytkownik NIE JEST zalogowany, wyrzucamy go na /login
    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    // Jeśli strona wymaga admina, a użytkownik nim NIE JEST, pokazujemy błąd
    if (requireAdmin && !isAdmin) {
        return (
            <div style={{ textAlign: 'center', marginTop: '50px', color: 'red' }}>
                <h2>Odmowa dostępu (403)</h2>
                <p>Nie masz uprawnień administratora, aby zobaczyć tę stronę.</p>
            </div>
        );
    }

    // Jeśli wszystko jest OK, renderujemy zawartość strony (Outlet)
    return (
        <NodesProvider>
            <Outlet />
        </NodesProvider>
    );
};