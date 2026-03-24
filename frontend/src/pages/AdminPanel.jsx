import React, { useState } from "react";
import { useNodes } from "../context/NodesContext";
import { addNewNode, KillNode, StopStartNode } from "../requestsAPI/nodesAPI";

import '../App.css';

export const AdminPanel = () => {
    const { nodes, nodesInfo } = useNodes();
    const [inputValue, setInputValue] = useState(1);

    const [message, setMessage] = useState("");
    const [isError, setIsError] = useState(false);

    const handleAddNode = async () => {
        setMessage("");
        const finalValue = inputValue === '' ? 1 : inputValue;

        try {
            await addNewNode(finalValue);
            setIsError(false);
            setMessage(`Węzeł #${finalValue} został pomyślnie utworzony!`);
            setInputValue(prev => prev + 1);
        } catch (error) {
            setIsError(true);
            setMessage(error.response?.data?.detail || `Wystąpił błąd podczas dodawania węzła #${finalValue}.`);
        }
    };

    const handleKillNode = async (id) => {
        if (window.confirm(`Czy na pewno chcesz definitywnie zabić proces węzła #${id}?`)) {
            setMessage("");
            try {
                await KillNode(id);
                setIsError(false);
                setMessage(`Proces węzła #${id} został całkowicie zlikwidowany.`);
            } catch (error) {
                setIsError(true);
                setMessage(error.response?.data?.detail || `Wystąpił błąd podczas usuwania węzła #${id}.`);
            }
        }
    };

    const handleStopStartNode = async (id, running) => {
        setMessage("");
        try {
            await StopStartNode(id, running);
            setIsError(false);
            setMessage(`Pomyślnie ${running ? 'zatrzymano' : 'wznowiono'} węzeł #${id}.`);
        } catch (error) {
            setIsError(true);
            setMessage(error.response?.data?.detail || `Błąd podczas zmiany statusu węzła #${id}.`);
        }
    };

    const handleInputChange = (e) => {
        const value = e.target.value;
        if (value === '') {
            setInputValue('');
            return;
        }
        const parsedValue = parseInt(value, 10);
        if (!isNaN(parsedValue) && parsedValue >= 1) {
            setInputValue(parsedValue);
        }
    };

    return (
        <div className="admin-container">
            <h1 style={{ marginBottom: '20px' }}>Panel Administratora</h1>

            {message && (
                <div
                    className={isError ? "error-msg" : "success-msg"}
                    style={{ marginBottom: '20px' }}
                >
                    {message}
                </div>
            )}

            {/* --- NOWY, PRZEPROJEKTOWANY PANEL GÓRNY --- */}
            <div className="node-card" style={{
                display: 'flex',
                flexWrap: 'wrap',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '40px',
                padding: '25px 30px',
                gap: '20px'
            }}>

                {/* Lewa strona: Informacje */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <h2 style={{ margin: 0, fontSize: '1.3rem', color: 'var(--primary)' }}>Zarządzanie klastrem</h2>
                    <p style={{ margin: 0, border: 'none', padding: 0, display: 'flex', alignItems: 'center' }}>
                        Aktywne procesy:
                        <span style={{
                            marginLeft: '12px',
                            background: 'var(--bg)',
                            border: '1px solid var(--border)',
                            color: 'var(--primary)',
                            fontWeight: '700',
                            fontSize: '1.1rem',
                            padding: '4px 12px',
                            borderRadius: '8px'
                        }}>
                            {nodes?.length || 0}
                        </span>
                    </p>
                </div>

                {/* Prawa strona: Formularz dodawania */}
                <div style={{
                    display: 'flex',
                    alignItems: 'flex-end',
                    gap: '12px',
                    background: 'var(--bg)',
                    padding: '16px 20px',
                    borderRadius: '12px',
                    border: '1px solid var(--border)'
                }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                        <label style={{
                            fontSize: '0.75rem',
                            color: 'var(--secondary)',
                            marginBottom: '6px',
                            fontWeight: '700',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px'
                        }}>
                            ID Węzła
                        </label>
                        <input
                            type="number"
                            min="1"
                            value={inputValue}
                            onChange={handleInputChange}
                            placeholder="Wpisz ID"
                            style={{
                                width: '90px',
                                margin: 0,
                                textAlign: 'center',
                                fontWeight: '600',
                                padding: '10px'
                            }}
                        />
                    </div>
                    <button
                        onClick={handleAddNode}
                        style={{
                            width: 'auto',
                            margin: 0,
                            padding: '10px 20px',
                            whiteSpace: 'nowrap' // Zapobiega łamaniu tekstu na przycisku
                        }}
                    >
                        + Uruchom nowy
                    </button>
                </div>

            </div>

            {/* --- SIATKA WĘZŁÓW --- */}
            <div className="nodes-grid">
                {nodes && nodes.map((node) => {
                    const id = node?.node_id;
                    const nodeDetail = nodesInfo?.[id];

                    const leader_id = nodeDetail?.leader_id || "Brak";
                    const process_status = node?.status;
                    const node_status = nodeDetail?.status || "OFFLINE";

                    const running = node_status === "ACTIVE";

                    return (
                        <div key={id} className="node-card">
                            <p><strong>ID Węzła</strong> <span>#{id}</span></p>
                            <p><strong>Leader</strong> <span>{leader_id}</span></p>
                            <p><strong>Proces</strong> <span>{process_status}</span></p>
                            <p>
                                <strong>Status</strong>
                                <span className={`status-pill ${running ? 'status-active' : 'status-inactive'}`}>
                                    {node_status}
                                </span>
                            </p>

                            <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                                <button
                                    onClick={() => handleStopStartNode(id, running)}
                                    style={{ flex: 2, margin: 0 }}
                                >
                                    {running ? "Zatrzymaj" : "Wznów"}
                                </button>
                                <button
                                    onClick={() => handleKillNode(id)}
                                    className="btn-danger"
                                    style={{ flex: 1, margin: 0 }}
                                >
                                    Kill
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};