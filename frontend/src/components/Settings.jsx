import React, { useState } from 'react';
import { QRCodeCanvas } from 'qrcode.react'; // Biblioteka do generowania QR z linku
import api from '../api';

export const Settings2FA = () => {
    const [qrUrl, setQrUrl] = useState('');
    const [secret, setSecret] = useState('');
    const [code, setCode] = useState('');
    const [message, setMessage] = useState('');

    // KROK 1: Generowanie sekretu i URL dla aplikacji
    const handleSetup = async () => {
        try {
            const res = await api.post('/auth/setup-2fa');
            setQrUrl(res.data.otpauth_url);
            setSecret(res.data.secret_manual);
        } catch (err) {
            setMessage('Błąd: ' + err.response?.data?.detail);
        }
    };

    // KROK 2: Potwierdzenie pierwszym kodem
    const handleConfirm = async () => {
        try {
            const res = await api.post('/auth/confirm-2fa', { code });
            setMessage(res.data.message);
            setQrUrl(''); // Ukrywamy QR po sukcesie
        } catch (err) {
            setMessage('Błędny kod: ' + err.response?.data?.detail);
        }
    };

    return (
        <div style={{ padding: '20px', border: '1px solid #ddd', marginTop: '20px' }}>
            <h3>Zabezpieczenie 2FA (Google Authenticator)</h3>
            {!qrUrl ? (
                <button onClick={handleSetup}>Włącz 2FA na tym koncie</button>
            ) : (
                <div>
                    <p>Zeskanuj kod QR w swojej aplikacji:</p>
                    <QRCodeCanvas value={qrUrl} size={200} />
                    <p>Lub wpisz ręcznie: <strong>{secret}</strong></p>
                    <input 
                        type="text" 
                        placeholder="Kod z aplikacji" 
                        value={code} 
                        onChange={e => setCode(e.target.value)} 
                    />
                    <button onClick={handleConfirm}>Potwierdź i aktywuj</button>
                </div>
            )}
            {message && <p>{message}</p>}
        </div>
    );
};