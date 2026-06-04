import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export const Login = () => {
    const { login } = useAuth();
    const navigate = useNavigate();

    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    
    const [step, setStep] = useState(1);
    const [totpCode, setTotpCode] = useState('');
    const [tempToken, setTempToken] = useState('');
    
    const [error, setError] = useState('');


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
            else if(err.response?.status === 422){
                const details = err.response?.data?.detail;
                console.log(details);

                if (Array.isArray(details)) {
                    const errorMessages = details.map(errObj => {
                        const field = errObj.loc[errObj.loc.length - 1];
                        const cleanMsg = errObj.msg.replace(/^Value error, /, "");
                        const fieldMap = { username: "Login", password: "Hasło" };
                        const label = fieldMap[field] || field;

                        return `${cleanMsg}`;
                    });

                    setError(errorMessages.join("\n"));
                } else {
                    setError("Wystąpił nieoczekiwany błąd");
                }
            
            }else if(err.response?.status === 401){
                setError(err.response?.data?.detail || 'Błąd rejestracji');
            }
        }
        
    };

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
            
            {error && <p className="error-msg" style={{ marginBottom: '20px' }}>{error}</p>}

            {step === 1 ? (
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