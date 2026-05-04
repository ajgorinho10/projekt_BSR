import React, { createContext, useState, useEffect, useContext } from 'react';
import {api, getAccessToken, setAccessToken, setLogout, GetisLogout} from '../api';


const AuthContext = createContext(null);


export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isLoading, setIsLoading] = useState(true);


    const checkAuthStatus = async () => {
        const islogout = await GetisLogout()
        console.log("Jest wylogowany:",islogout)
        if(islogout){
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


    const login = async (accessToken) => {
        setAccessToken(accessToken);
        setLogout(false);
        await checkAuthStatus();
    };

    const logout = async () => {
        const response = await api.post('/auth/logout');
        setLogout(true);
        setAccessToken(null);
        setUser(null);

        window.location.href = '/login';
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