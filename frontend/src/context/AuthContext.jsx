import React, { createContext, useState, useEffect, useContext } from 'react';
import api from '../api'; // Twój przechwytywacz Axios!

// 1. Tworzymy Kontekst
const AuthContext = createContext(null);

// 2. Tworzymy Providera (Dostawcę), który owinie naszą aplikację
export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isLoading, setIsLoading] = useState(true); // Ważne: zapobiega mruganiu ekranu przy odświeżaniu

    // Funkcja pobierająca najświeższe dane użytkownika z backendu
    const checkAuthStatus = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            setUser(null);
            setIsLoading(false);
            return;
        }

        try {
            // Uderzamy na Twój chroniony endpoint. 
            // Jeśli token wygasł, nasz interceptor z api.js sam go odświeży!
            const response = await api.get('/auth/me');
            setUser(response.data); // Ustawiamy pełny obiekt: {id, username, role, totp_enabled}
        } catch (error) {
            console.error("Błąd weryfikacji sesji:", error);
            setUser(null);
        } finally {
            setIsLoading(false); // Kończymy ładowanie niezależnie od wyniku
        }
    };

    // Uruchamiamy weryfikację przy pierwszym odpaleniu aplikacji (odświeżenie karty przeglądarki)
    useEffect(() => {
        checkAuthStatus();
    }, []);

    // Funkcja wywoływana po udanym logowaniu (zapisuje tokeny i pobiera usera)
    const login = async (accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        await checkAuthStatus(); // Od razu po zapisaniu tokenów, pobieramy dane usera!
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