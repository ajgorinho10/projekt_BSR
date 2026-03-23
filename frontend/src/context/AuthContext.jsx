import React, { createContext, useState, useEffect, useContext } from 'react';
import api from '../api';


const AuthContext = createContext(null);


export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isLoading, setIsLoading] = useState(true);


    const checkAuthStatus = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            setUser(null);
            setIsLoading(false);
            return;
        }

        try {
            const response = await api.get('/auth/me');
            setUser(response.data);
        } catch (error) {
            console.error("Błąd weryfikacji sesji:", error);
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        checkAuthStatus();
    }, []);


    const login = async (accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        await checkAuthStatus();
    };

    // Funkcja wylogowania
    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
        
        // Opcjonalnie: można tu wywołać api.post('/auth/logout'), aby zablokować token w backendzie
        window.location.href = '/login'; // Przekierowanie
    };

    // To, co udostępniamy reszcie aplikacji
    const contextValue = {
        user,
        checkAuthStatus,
        isLoading,
        login,
        logout,
        isAuthenticated: !!user, // Wygodny boolean (true/false)
        isAdmin: user?.role === 'admin' // Wygodny sprawdzacz ról
    };
//{!isLoading ? children : <div style={{textAlign: 'center', marginTop: '50px'}}>Ładowanie systemu...</div>}
    return (
        <AuthContext.Provider value={contextValue}>
            {/* Nie renderujemy aplikacji, dopóki nie sprawdzimy kim jest user */}
            {!isLoading ? children : <div style={{textAlign: 'center', marginTop: '50px'}}>Ładowanie systemu...</div>}

        </AuthContext.Provider>
    );
};

// 3. Wygodny Hook (żeby nie pisać wszędzie useContext(AuthContext))
export const useAuth = () => {
    return useContext(AuthContext);
};