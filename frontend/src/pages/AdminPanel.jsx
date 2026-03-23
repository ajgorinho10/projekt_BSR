import React, { useState } from "react";
import { useNodes } from "../context/NodesContext";
import { addNewNode, KillNode, StopStartNode } from "../requestsAPI/nodesAPI";

import '../App.css';

export const AdminPanel = () => {
    const { nodes, nodesInfo } = useNodes();
    const [inputValue, setInputValue] = useState(1);

    const addNodeButton = () => {
        const finalValue = inputValue === '' ? 1 : inputValue;
        addNewNode(finalValue);
    }

    const KillNodeButton = (id) => {
        if (window.confirm(`Czy na pewno chcesz definitywnie zabić proces #${id}?`)) {
            KillNode(id);
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
            <h1>Panel Administratora</h1>
            
            <div className="node-card" style={{ textAlign: 'center', marginBottom: '30px' }}>
                <p style={{ justifyContent: 'center', fontWeight: '500' }}>
                    Aktywne wątki: <span style={{ marginLeft: '8px', color: 'var(--primary-color)' }}>{nodes?.length || 0}</span>
                </p>
                <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
                    <input 
                        type="number" 
                        min="1"
                        value={inputValue} 
                        onChange={handleInputChange}
                        placeholder="Ilość"
                    />
                    <button onClick={addNodeButton}>Dodaj wątek</button>
                </div>
            </div>

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
                                    onClick={() => StopStartNode(id, running)}
                                    style={{ flex: 2 }}
                                >
                                    {running ? "Zatrzymaj" : "Wznów"}
                                </button>
                                <button 
                                    onClick={() => KillNodeButton(id)} 
                                    className="btn-danger"
                                    style={{ flex: 1 }}
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