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
            
            // Axios dostarczy dane w response.data, jeśli status był 2xx
            if (response.data.step === "2fa_required") {
                setTempToken(response.data.preauth_token);
                setStep(2);
            } else {
                await login(response.data.access_token, response.data.refresh_token);
                navigate('/dashboard');
            }
        } catch (err) {
            // Obsługa błędów Axios
            const message = err.response?.data?.detail || 'Błędny login lub hasło.';
            setError(message);
        }
    };

    // Krok 2: Wysłanie kodu TOTP
    const handleVerifyTotp = async (e) => {
        e.preventDefault();
        setError('');
        try {
            // Wysyłamy kod z aplikacji i tymczasowy token, który udowadnia, że znamy hasło
            const response = await api.post('/auth/verify-2fa', { 
                preauth_token: tempToken, // Nazwa zgodna z Twoim schematem Verify2FA
                code: totpCode 
            });
            
            // Jeśli kod jest poprawny, backend wydaje właściwe tokeny
            await login(response.data.access_token, response.data.refresh_token);
            navigate('/dashboard');
        } catch (err) {
            setError('Nieprawidłowy kod 2FA.');
        }
    };

    return (
        <div style={{ maxWidth: '300px', margin: '50px auto' }}>
            <h2>Logowanie</h2>
            {error && <p style={{ color: 'red' }}>{error}</p>}

            {step === 1 ? (
                // WIDOK 1: Standardowe logowanie
                <form onSubmit={handleInitialLogin}>
                    <div>
                        <label>Login:</label>
                        <input type="text" value={username} onChange={e => setUsername(e.target.value)} required />
                    </div>
                    <div>
                        <label>Hasło:</label>
                        <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
                    </div>
                    <button type="submit" style={{ marginTop: '10px' }}>Zaloguj</button>
                </form>
            ) : (
                // WIDOK 2: Weryfikacja 2FA
                <form onSubmit={handleVerifyTotp}>
                    <p>Wprowadź 6-cyfrowy kod z aplikacji uwierzytelniającej:</p>
                    <div>
                        <input 
                            type="text" 
                            maxLength="6" 
                            value={totpCode} 
                            onChange={e => setTotpCode(e.target.value)} 
                            required 
                            placeholder="000000"
                        />
                    </div>
                    <button type="submit" style={{ marginTop: '10px' }}>Potwierdź kod</button>
                    <button type="button" onClick={() => setStep(1)} style={{ marginLeft: '10px' }}>Cofnij</button>
                </form>
            )}
        </div>
    );
};