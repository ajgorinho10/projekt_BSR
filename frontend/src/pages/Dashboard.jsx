import React, { useState } from "react";
import { useNodes } from "../context/NodesContext.jsx";
import { useNodeWebSocket } from "../hooks/useNodeWebSocket.js"; // Dostosuj ścieżkę importu!
import api from "../api.js";

export const DashboardPage = () => {
    const { nodes, nodesInfo } = useNodes();
    const numberOfNodes = nodes?.length || 0;

    const [selectedNode, setSelectedNode] = useState("");
    const [data, setData] = useState("");
    const [deleteId, setDeleteId] = useState("");
    const [refreshKey, setRefreshKey] = useState(0);


    const {
        wsStatus,
        message,
        isError,
        sendDataToNode,
        deleteDataToNode,
        clearMessage
    } = useNodeWebSocket(selectedNode, nodes, setData,refreshKey);

    const handleSendData = () => {
        sendDataToNode(data);
    };

    const handleDeleteData = () => {
        deleteDataToNode(deleteId);
        setDeleteId("");
    };

    const refreshToken = () =>{
        const tmp = selectedNode;
        setRefreshKey(prev=>prev+1);
        clearMessage();
        setSelectedNode("");
        setData("");
        setDeleteId("");

        setTimeout(() => {
        setSelectedNode(tmp);
    }, 2);
    };

    const disconnect = () =>{
        setSelectedNode("");
        setData("");
        setDeleteId("");

        clearMessage();
    }

    const getStatusColor = () => {
        if (wsStatus === "CONNECTED") return "#24a159";
        if (wsStatus === "CONNECTING") return "#f39c12";
        return "var(--danger)";
    };

    return (
        <div className="admin-container">
            <p style={{ fontSize: '1.2rem', marginBottom: '20px' }}>
                Ilość aktywnych węzłów: <strong>{numberOfNodes}</strong>
            </p>

            {numberOfNodes > 0 && (
                <div className="node-card" style={{ display: "flex", gap: "25px", alignItems: "flex-start" }}>

                    {/* LEWA KOLUMNA: WYBÓR WĘZŁA */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "2px" }}>
                            <p style={{ marginBottom: "5px" }}><strong>Wybierz węzeł</strong></p>
                            {selectedNode && (
                                <span style={{ fontSize: "0.8rem", fontWeight: "600", color: getStatusColor() }}>
                                    ● {wsStatus}
                                </span>
                            )}
                        </div>
                        <select
                            value={selectedNode}
                            onChange={(e) => setSelectedNode(e.target.value)}
                            className="custom-select"
                        >
                            <option value="" disabled>-- Wybierz z listy --</option>
                            {nodes.map((node) => (
                                <option key={node?.node_id} value={node?.node_id}>Węzeł #{node?.node_id}</option>
                            ))}
                        </select>
                        {isError?(
                            <button onClick={refreshToken} style={{ marginTop: '10px', backgroundColor: '#24a159' }}>Odśwież</button>
                        ):(
                            ((wsStatus === "CONNECTED")&&<button onClick={disconnect} style={{ marginTop: '10px', backgroundColor: '#24a159' }}>Rozłącz</button>)
                        )}
                    </div>

                    {/* ŚRODKOWA KOLUMNA: DODAWANIE */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderLeft: "1px solid #eee", paddingLeft: "20px" }}>
                        <p style={{ marginBottom: "10px" }}><strong>Dodaj dane</strong></p>
                        <input
                            type="text"
                            placeholder="Treść danych..."
                            value={data}
                            onChange={(e) => setData(e.target.value)}
                            disabled={wsStatus !== "CONNECTED"}
                        />
                        <button onClick={handleSendData} disabled={wsStatus !== "CONNECTED"} style={{ marginTop: '10px' }}>
                            Wyślij Dane
                        </button>
                    </div>

                    {/* PRAWA KOLUMNA: USUWANIE */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderLeft: "1px solid #eee", paddingLeft: "20px" }}>
                        <p style={{ marginBottom: "10px" }}><strong>Usuń dane</strong></p>
                        <input
                            type="number"
                            placeholder="ID rekordu (np. 15)"
                            value={deleteId}
                            onChange={(e) => setDeleteId(e.target.value)}
                            disabled={wsStatus !== "CONNECTED"}
                        />
                        <button
                            onClick={handleDeleteData}
                            disabled={wsStatus !== "CONNECTED"}
                            style={{ marginTop: '10px', backgroundColor: 'var(--danger)' }}
                        >
                            Usuń po ID
                        </button>
                    </div>
                </div>
            )}

            {message && (
                <div className={isError ? "error-msg" : "success-msg"} style={{ marginTop: '20px', textAlign: 'center' }}>
                    {message}
                </div>
            )}

            <p style={{ marginTop: "40px", marginBottom: "20px", fontSize: "1.2rem" }}>
                <strong>Lista dostępnych węzłów</strong>
            </p>

            <div className="nodes-grid">
                {nodes && nodes.map((node) => {
                    const id = node?.node_id;
                    const nodeDetail = nodesInfo?.[id];

                    const process_status = node?.status;
                    const node_status = nodeDetail?.status || "OFFLINE";
                    const running = node_status === "ACTIVE";

                    return (
                        <div key={id} className="node-card">
                            <p><strong>ID Węzła</strong> <span>#{id}</span></p>
                            <p><strong>Proces</strong> <span>{process_status}</span></p>
                            <p>
                                <strong>Status</strong>
                                <span className={`status-pill ${running ? 'status-active' : 'status-inactive'}`}>
                                    {node_status}
                                </span>
                            </p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};