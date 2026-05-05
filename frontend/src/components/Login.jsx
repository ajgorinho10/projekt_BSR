import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export const Login = () => {
    const { login } = useAuth();
    const navigate = useNavigate();

    // Stany formularza
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    
    // Stany dla 2FA
    const [step, setStep] = useState(1); // 1 = Login/Hasło, 2 = Kod TOTP
    const [totpCode, setTotpCode] = useState('');
    const [tempToken, setTempToken] = useState(''); // Tymczasowy token z kroku 1
    
    const [error, setError] = useState('');

    // Krok 1: Wysłanie loginu i hasła
    const handleInitialLogin = async (e) => {
        e.preventDefault();
        setError('');
        try {
            const response = await api.post('/auth/login', { username, password });
            
            if (response.data.step === "2fa_required") {
                setTempToken(response.data.preauth_token);
                setStep(2);
            } else {
                await login(response.data.access_token);
                navigate('/dashboard');
            }
        } catch (err) {    
            if(err.response?.status === 429){
                setError("Zbyt dużo błędnych prób logowania zaczekaj 1 minutę");
                return;
            }

            const newMsgUsername = (err.response?.data?.detail[0]?.loc[1] +" : "+ err.response?.data?.detail[0]?.msg) || ""
            
            if(err.response?.data?.detail[1] !== undefined){
                const newMsgPassword = (err.response?.data?.detail[1]?.loc[1] +" : "+ err.response?.data?.detail[1]?.msg) || ""
                setError((newMsgUsername + "\n" + newMsgPassword) || 'Błąd rejestracji');
                return
            }

            setError((newMsgUsername + "\n") || 'Błąd rejestracji');
        }
    };

    // Krok 2: Wysłanie kodu TOTP
    const handleVerifyTotp = async (e) => {
        e.preventDefault();
        setError('');
        try {
            const response = await api.post('/auth/verify-2fa', { 
                preauth_token: tempToken, 
                code: totpCode 
            });
            
            await login(response.data.access_token, response.data.refresh_token);
            navigate('/dashboard');
        } catch (err) {
            if(err.response?.status === 429){
                setError("Zbyt dużo błędnych prób zaczekaj 1 minutę");
                return;
            }
            setError('Nieprawidłowy kod 2FA.');
        }
    };

    return (
        <div className="container" style={{ margin: 'auto', marginTop: '10vh' }}>
            <h2>{step === 1 ? 'Zaloguj się' : 'Weryfikacja 2FA'}</h2>
            
            {/* Wyświetlanie błędów z wykorzystaniem klasy CSS z App.css */}
            {error && <p className="error-msg" style={{ marginBottom: '20px' }}>{error}</p>}

            {step === 1 ? (
                // WIDOK 1: Standardowe logowanie
                <form onSubmit={handleInitialLogin}>
                    <div style={{ marginBottom: '15px' }}>
                        <label style={{ fontSize: '0.9rem', color: 'var(--secondary)', fontWeight: '500' }}>
                            Login
                        </label>
                        <input 
                            type="text" 
                            value={username} 
                            onChange={e => setUsername(e.target.value)} 
                            required 
                            placeholder="Wpisz swój login"
                        />
                    </div>
                    <div style={{ marginBottom: '25px' }}>
                        <label style={{ fontSize: '0.9rem', color: 'var(--secondary)', fontWeight: '500' }}>
                            Hasło
                        </label>
                        <input 
                            type="password" 
                            value={password} 
                            onChange={e => setPassword(e.target.value)} 
                            required 
                            placeholder="Wpisz swoje hasło"
                        />
                    </div>
                    <button type="submit">Zaloguj</button>
                </form>
            ) : (
                // WIDOK 2: Weryfikacja 2FA
                <form onSubmit={handleVerifyTotp}>
                    <p style={{ marginBottom: '20px' }}>
                        Wprowadź 6-cyfrowy kod z aplikacji uwierzytelniającej.
                    </p>
                    <div style={{ marginBottom: '25px' }}>
                        <input 
                            type="text" 
                            maxLength="6" 
                            value={totpCode} 
                            onChange={e => setTotpCode(e.target.value)} 
                            required 
                            placeholder="000 000"
                            style={{ textAlign: 'center', fontSize: '1.2rem', letterSpacing: '2px' }}
                        />
                    </div>
                    <button type="submit">Potwierdź kod</button>
                    <button 
                        type="button" 
                        onClick={() => setStep(1)} 
                        className="btn-danger" 
                        style={{ marginTop: '10px' }}
                    >
                        Cofnij
                    </button>
                </form>
            )}
        </div>
    );
};