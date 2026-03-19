import React, { useState } from 'react';
import api from '../api';
import { useNavigate } from 'react-router-dom';

export const Register = () => {
    const [formData, setFormData] = useState({ username: '', password: '' });
    const [msg, setMsg] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await api.post('/auth/register', formData);
            setMsg('Zarejestrowano pomyślnie! Zaraz zostaniesz przekierowany...');
            setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            setMsg(err.response?.data?.detail || 'Błąd rejestracji');
        }
    };

    return (
        <div style={{ maxWidth: '300px', margin: 'auto' }}>
            <h2>Rejestracja</h2>
            <form onSubmit={handleSubmit}>
                <input type="text" placeholder="Login" onChange={e => setFormData({...formData, username: e.target.value})} required /><br/>
                <input type="password" placeholder="Hasło" onChange={e => setFormData({...formData, password: e.target.value})} required /><br/>
                <button type="submit">Zarejestruj</button>
            </form>
            <p>{msg}</p>
        </div>
    );
};