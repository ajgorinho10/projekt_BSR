import React, { useState } from 'react';
import api from '../api';
import { useNavigate } from 'react-router-dom';

export const Register = () => {
    const [formData, setFormData] = useState({ username: '', password: '' });
    const [msg, setMsg] = useState('');
    const [isSuccess, setIsSuccess] = useState(false); // Flaga do odróżnienia sukcesu od błędu
    
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMsg('');
        
        try {
            const response = await api.post('/auth/register', formData);
            setIsSuccess(true);
            setMsg('Zarejestrowano pomyślnie! Zaraz zostaniesz przekierowany...');
            setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            setIsSuccess(false);
            const newMsgUsername = (err.response?.data?.detail[0]?.loc[1] +" : "+ err.response?.data?.detail[0]?.msg) || ""
            
            if(err.response?.data?.detail[1] !== undefined){
                const newMsgPassword = (err.response?.data?.detail[1]?.loc[1] +" : "+ err.response?.data?.detail[1]?.msg) || ""
                setMsg((newMsgUsername + "\n" + newMsgPassword) || 'Błąd rejestracji');
                return
            }

            setMsg((newMsgUsername + "\n") || 'Błąd rejestracji');
        }
    };

    return (
        <div className="container" style={{ margin: 'auto', marginTop: '10vh' }}>
            <h2>Rejestracja</h2>
            
            {/* Dynamiczne stylowanie komunikatu (sukces / błąd) */}
            {msg && (
                <p 
                    className={isSuccess ? "success-msg" : "error-msg"} 
                    style={{ marginBottom: '20px' }}
                >
                    {msg}
                </p>
            )}

            <form onSubmit={handleSubmit}>
                <div style={{ marginBottom: '15px' }}>
                    <label style={{ fontSize: '0.9rem', color: 'var(--secondary)', fontWeight: '500' }}>
                        Login
                    </label>
                    <input 
                        type="text" 
                        placeholder="Wpisz swój login" 
                        value={formData.username}
                        onChange={e => setFormData({...formData, username: e.target.value})} 
                        required 
                    />
                </div>
                
                <div style={{ marginBottom: '25px' }}>
                    <label style={{ fontSize: '0.9rem', color: 'var(--secondary)', fontWeight: '500' }}>
                        Hasło
                    </label>
                    <input 
                        type="password" 
                        placeholder="Wpisz swoje hasło" 
                        value={formData.password}
                        onChange={e => setFormData({...formData, password: e.target.value})} 
                        required 
                    />
                </div>
                
                <button type="submit">Zarejestruj</button>
            </form>
        </div>
    );
};