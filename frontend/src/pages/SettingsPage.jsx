import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { promoteTo, updateUserName, updateUserPassword, updateUserDisableTOTP } from "../requestsAPI/userAPI";

export const SettingsPage = () => {
    const { user, checkAuthStatus } = useAuth();

    const [newPass, setNewPass] = useState("");
    const [newLogin, setNewLogin] = useState("");
    
    // Dodajemy nowe stany do obsługi komunikatów!
    const [message, setMessage] = useState('');
    const [isError, setIsError] = useState(false);

    const changeRole = async () => {
        setMessage(''); // Czyścimy poprzednie komunikaty
        const rola = user.role === "user" ? "admin" : "user";
        await promoteTo(rola);
        await checkAuthStatus();
        setIsError(false);
        setMessage(`Rola zmieniona na ${rola}`);
    };

    const passwordChange = async () => {
        if (!newPass) return;
        setMessage('');
        try {
            await updateUserPassword(newPass);
            setNewPass("");
            await checkAuthStatus();
            setIsError(false);
            setMessage("Hasło zostało pomyślnie zmienione!");
        } catch (error) {
            setIsError(true);
            setMessage(error.response?.data?.detail || "Błąd podczas zmiany hasła.");
        }
    };

    const loginChange = async () => {
        if (!newLogin) return;
        setMessage(''); // Czyścimy stare wiadomości
        try {
            // Wywołujemy funkcję aktualizującą
            await updateUserName(newLogin);
            setNewLogin("");
            await checkAuthStatus();
            // Uwaga: Jeśli masz logikę, która wylogowuje po zmianie loginu,
            // to kod poniżej może nie zdążyć się wyświetlić.
            setIsError(false);
            setMessage("Login zmieniony pomyślnie!"); 
        } catch (error) {
            // TUTAJ ŁAPIEMY BŁĄD Z FASTAPI (np. "Nazwa użytkownika jest zajęta !")
            setIsError(true);
            setMessage(error.response?.data?.detail || "Wystąpił błąd podczas zmiany loginu.");
        }
    };

    const disableTOTP = async () => {
        setMessage('');
        if (window.confirm("Czy na pewno chcesz wyłączyć zabezpieczenie TOTP 2FA?")) {
            try {
                await updateUserDisableTOTP();
                await checkAuthStatus();
                setIsError(false);
                setMessage("Zabezpieczenie TOTP zostało wyłączone.");
            } catch (error) {
                setIsError(true);
                setMessage("Błąd podczas wyłączania TOTP.");
            }
        }
    };

    return (
        <div className="container">
            <h2>Informacje o profilu</h2>
            
            {/* Wyświetlanie komunikatów o sukcesie lub błędzie */}
            {message && (
                <p className={isError ? "error-msg" : "success-msg"} style={{ marginBottom: '20px' }}>
                    {message}
                </p>
            )}

            <div style={{ marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid var(--border)' }}>
                <p><strong>Login:</strong> {user.username}</p>
                <p><strong>Rola:</strong> {user.role}</p>
                <p style={{ display: 'flex', alignItems: 'center' }}>
                    <strong>TOTP 2FA:</strong> 
                    <span 
                        className={`status-pill ${user.totp_enabled ? 'status-active' : 'status-inactive'}`} 
                        style={{ marginLeft: '10px' }}
                    >
                        {user.totp_enabled ? "WŁĄCZONE" : "WYŁĄCZONE"}
                    </span>
                </p>
            </div>

            <h2>Ustawienia</h2>

            <div style={{ marginBottom: '25px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <p style={{ margin: 0 }}>Twoja obecna rola to: <strong>{user.role}</strong></p>
                    <button 
                        onClick={changeRole} 
                        style={{ width: 'auto', padding: '6px 16px', margin: 0 }}
                    >
                        Zmień na {user.role === "user" ? "admin" : "user"}
                    </button>
                </div>
            </div>

            <div style={{ marginBottom: '25px' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--secondary)', fontWeight: '500' }}>
                    Zmień hasło
                </label>
                <input
                    type="password" 
                    placeholder="Wpisz nowe hasło"
                    value={newPass}
                    onChange={(e) => setNewPass(e.target.value)} 
                />
                <button onClick={passwordChange}>Zaktualizuj hasło</button>
            </div>

            <div style={{ marginBottom: '25px' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--secondary)', fontWeight: '500' }}>
                    Zmień login
                </label>
                <input
                    type="text" 
                    placeholder="Wpisz nowy login"
                    value={newLogin}
                    onChange={(e) => setNewLogin(e.target.value)} 
                />
                <button onClick={loginChange}>Zaktualizuj login</button>
                <p style={{ fontSize: '0.8rem', marginTop: '8px', color: 'var(--danger)' }}>
                    * Po pomyślnej zmianie loginu nastąpi automatyczne wylogowanie.
                </p>
            </div>

            <div style={{ marginTop: '30px', paddingTop: '20px', borderTop: '1px solid var(--border)' }}>
                {user.totp_enabled ? (
                    <button onClick={disableTOTP} className="btn-danger">
                        Wyłącz zabezpieczenie TOTP 2FA
                    </button>
                ) : (
                    <p style={{ textAlign: 'center', margin: 0 }}>
                        Zabezpieczenie TOTP jest wyłączone. Aktywuj je w zakładce <strong>2FA</strong>.
                    </p>
                )}
            </div>
        </div>
    );
};