import React, { createContext, useState, useEffect, useContext,useRef } from 'react';

const NodesContext = createContext(null);


export const NodesProvider = ({ children }) => {
    const [nodes,setNodes] = useState([]);
    const [nodesInfo,setNodesInfo] = useState({});

    const ws = useRef(null);

    useEffect(() => {   
        ws.current = new WebSocket("ws://127.0.0.1:8000/nodes/ws")

        ws.current.onopen = () => {
            console.log('Połączono z serwerem WebSocket');
        };

        ws.current.onmessage = (event) => {
            const parsedData = JSON.parse(event.data);
            setNodes(parsedData.nodes);
            setNodesInfo(parsedData.node_details);
        };

        ws.current.onclose = () => {
            console.log('Rozłączono z serwerem WebSocket');
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