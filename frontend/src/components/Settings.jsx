import React, { useState } from 'react';
import { QRCodeCanvas } from 'qrcode.react'; 
import { useAuth } from '../context/AuthContext';
import api from '../api';

export const Settings2FA = () => {
    const { user, checkAuthStatus } = useAuth();
    const [qrUrl, setQrUrl] = useState('');
    const [secret, setSecret] = useState('');
    const [code, setCode] = useState('');
    const [message, setMessage] = useState('');
    const [isSuccess, setIsSuccess] = useState(false);

    
    if (user?.totp_enabled) {
        return (
            <div className="container" style={{ textAlign: 'center' }}>
                <h2>Zabezpieczenie 2FA</h2>
                <p className="success-msg" style={{ marginTop: '20px' }}>
                    Uwierzytelnianie dwuskładnikowe (TOTP) jest już <strong>aktywne</strong> na Twoim koncie.
                </p>
                <p style={{ fontSize: '0.9rem', color: 'var(--secondary)', marginTop: '15px' }}>
                    Aby je wyłączyć, przejdź do zakładki <strong>Ustawienia</strong>.
                </p>
            </div>
        );
    }

    
    const handleSetup = async () => {
        setMessage('');
        try {
            const res = await api.post('/auth/setup-2fa');
            setQrUrl(res.data.otpauth_url);
            setSecret(res.data.secret_manual);
        } catch (err) {
            setIsSuccess(false);
            setMessage(err.response?.data?.detail || 'Wystąpił błąd podczas generowania kodu.');
        }
    };

    
    const handleConfirm = async () => {
        setMessage('');
        try {
            const res = await api.post('/auth/confirm-2fa', { code });
            setIsSuccess(true);
            setMessage(res.data.message || 'Zabezpieczenie 2FA zostało pomyślnie aktywowane!');
            setQrUrl('');
            await checkAuthStatus();
        } catch (err) {
            setIsSuccess(false);
            setMessage(err.response?.data?.detail || 'Błędny kod z aplikacji.');
        }
    };

    return (
        <div className="container">
            <h2>Aktywacja 2FA</h2>
            
            {message && (
                <p className={isSuccess ? "success-msg" : "error-msg"} style={{ marginBottom: '20px' }}>
                    {message}
                </p>
            )}

            {!qrUrl && !isSuccess ? (
                
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                    <p style={{ marginBottom: '30px', color: 'var(--secondary)', lineHeight: '1.6' }}>
                        Zwiększ bezpieczeństwo swojego konta. Do logowania będzie wymagane hasło oraz jednorazowy kod z aplikacji takich jak <strong>Google Authenticator</strong> lub <strong>Authy</strong>.
                    </p>
                    <button onClick={handleSetup}>Skonfiguruj 2FA</button>
                </div>
            ) : !isSuccess && qrUrl ? (
                
                <div style={{ textAlign: 'center' }}>
                    <p style={{ fontWeight: '500', marginBottom: '10px' }}>
                        1. Zeskanuj ten kod QR w swojej aplikacji:
                    </p>
                    
                    <QRCodeCanvas value={qrUrl} size={180} />
                    
                    <p style={{ marginTop: '20px', fontSize: '0.9rem', color: 'var(--secondary)' }}>
                        Nie możesz zeskanować kodu? Wpisz ręcznie poniższy klucz:
                    </p>
                    <div style={{ 
                        background: '#f5f5f5', 
                        padding: '10px', 
                        borderRadius: '8px', 
                        letterSpacing: '1px', 
                        fontWeight: '600',
                        margin: '10px 0 30px 0',
                        color: 'var(--primary)'
                    }}>
                        {secret}
                    </div>

                    <p style={{ fontWeight: '500', marginBottom: '15px' }}>
                        2. Przepisz 6-cyfrowy kod z aplikacji:
                    </p>
                    <div style={{ marginBottom: '20px' }}>
                        <input 
                            type="text" 
                            maxLength="6"
                            placeholder="000 000" 
                            value={code} 
                            onChange={e => setCode(e.target.value)} 
                            style={{ textAlign: 'center', fontSize: '1.2rem', letterSpacing: '2px' }}
                        />
                    </div>
                    
                    <button onClick={handleConfirm}>Potwierdź i aktywuj</button>
                </div>
            ) : null}
        </div>
    );
};