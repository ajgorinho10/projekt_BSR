import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

import { NodesProvider } from '../context/NodesContext';

export const ProtectedRoute = ({ requireAdmin = false }) => {
    const { isAuthenticated, isAdmin, isLoading } = useAuth();


    if (isLoading) {
        return <div style={{ textAlign: 'center', marginTop: '50px' }}>Sprawdzanie uprawnień...</div>;
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    if (requireAdmin && !isAdmin) {
        return (
            <div style={{ textAlign: 'center', marginTop: '50px', color: 'red' }}>
                <h2>Odmowa dostępu (403)</h2>
                <p>Nie masz uprawnień administratora, aby zobaczyć tę stronę.</p>
            </div>
        );
    }

    return (
        <NodesProvider>
            <Outlet />
        </NodesProvider>
    );
};