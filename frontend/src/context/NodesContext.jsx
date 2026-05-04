import React, { createContext, useState, useEffect, useContext,useRef } from 'react';
import { parsePath } from 'react-router-dom';
import {api, getAccessToken} from '../api';

const NodesContext = createContext(null);


export const NodesProvider = ({ children }) => {
    const [nodes,setNodes] = useState([]);
    const [nodesInfo,setNodesInfo] = useState({});

    const ws = useRef(null);

    useEffect(() => {
        let timeoutId;
        let isMounted = true;

        const connectWebSocket = () => {
            const token = getAccessToken();
            
            if (!token) {
                console.warn("Brak tokena, wstrzymuję połączenie WebSocket.");
                return;
            }

            console.log("Próba nawiązania połączenia WebSocket...");
            ws.current = new WebSocket(`ws://127.0.0.1:8000/ws/?token=${token}`);

            ws.current.onopen = () => {
                console.log('Połączono z bezpiecznym serwerem WebSocket');
            };

            ws.current.onmessage = (event) => {
                const parsedData = JSON.parse(event.data);
                setNodes(parsedData.nodes);
                setNodesInfo(parsedData.node_details);
            };


            ws.current.onclose = async (event) => {
                console.warn('Rozłączono z serwerem WebSocket.');
                
                if (isMounted) {
                    if(event.code === 1008 || event.code === 1006){
                        const req = await api.get("/auth/me");
                    }

                    console.log('Ponawiam połączenie za 3 sekundy...');
                    timeoutId = setTimeout(connectWebSocket, 3000);             
                }
            };

            ws.current.onerror = (error) => {
                setNodes([]);
                setNodesInfo({});
                ws.current.close(); 
            };
        };


        connectWebSocket();

        const handleBeforeUnload = () => {
            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                ws.current.close();
            }
        };

        window.addEventListener("beforeunload", handleBeforeUnload);

        return () => {
            isMounted = false;
            clearTimeout(timeoutId);
            window.removeEventListener("beforeunload", handleBeforeUnload);
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []);


    const contextValue = {
        nodes,
        nodesInfo
    };

    return (
        <NodesContext.Provider value={contextValue}>
            {children}
        </NodesContext.Provider>
    );
};

export const useNodes = () => {
    return useContext(NodesContext);
};