import { useState, useEffect, useRef } from "react";
import api from "../api.js";

export const useNodeWebSocket = (selectedNode, nodes, onSuccess,refreshKey) => {
    const [wsStatus, setWsStatus] = useState("DISCONNECTED");
    const [message, setMessage] = useState("");
    const [isError, setIsError] = useState(false);
    const [dataFromNode,setDataFromNode] = useState([]);

    const wsRef = useRef(null);

    const foundNode = nodes.find(node => String(node?.node_id) === String(selectedNode));
    const wsUrl = foundNode ? foundNode.url.replace(/^http/, 'ws') + "/ws/client" : null;


    useEffect(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        if (!wsUrl) {
            setWsStatus("DISCONNECTED");
            return;
        }

        api.get("/auth/me");
        setWsStatus("CONNECTING");
        const socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            setWsStatus("CONNECTED");
            setIsError(false);
            setMessage(`Połączono z węzłem #${selectedNode}.`);
        };

        socket.onmessage = (event) => {
            const response = JSON.parse(event.data);

            if (response.status === "error") {
                setIsError(true);
                setMessage(response.error || response.message || "Błąd węzła.");
            } else {
                setIsError(false);
                setMessage(response.message || "Lider pomyślnie zapisał dane!");
                console.log("odpowiedz:",response);
                if(response?.data){

                    if(response?.data_type === "new"){
                        setDataFromNode(response?.data || []);

                    }else if(response?.data_type === "add_to_list"){

                        setDataFromNode((prevData)=>{
                            const newItem = response?.data;
                            if (prevData.find(item => item.id === newItem.id)) {
                                return prevData;
                            }

                            return [...prevData, response?.data];
                        });
                    }else if(response?.data_type === "delete_from_list"){
                        setDataFromNode(prev => prev.filter(item => Number(item.id) !== Number(response?.data)));
                    }
                }else if(response?.data_id){
                    console.log("id",response?.data_id)
                }
            }
        };

        socket.onclose = () => {
            setWsStatus("DISCONNECTED");
        };

        socket.onerror = (error) => {
            console.error("Błąd WebSocket:", error);
            setWsStatus("DISCONNECTED");
            setIsError(true);
            setMessage("Błąd połączenia. Węzeł może być wyłączony.");
        };

        wsRef.current = socket;

        return () => {
            if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
                socket.close();
            }
        };
    }, [wsUrl]);

    const sendDataToNode = (dataToSend) => {
        setMessage("");

        if (!selectedNode) {
            setIsError(true);
            setMessage("Proszę wybrać węzeł z listy!");
            return;
        }

        if (dataToSend.trim() === "") {
            setIsError(true);
            setMessage("Proszę wprowadzić dane do wysłania!");
            return;
        }

        if (wsStatus !== "CONNECTED" || !wsRef.current) {
            setIsError(true);
            setMessage("Brak aktywnego połączenia z węzłem!");
            return;
        }

        const taskId = "task_" + Date.now();
        const token = localStorage.getItem("access_token");

        const payload = {
            action: "save_data",
            data: dataToSend,
            task_id: taskId,
            token: token,
        };

        wsRef.current.send(JSON.stringify(payload));

        setIsError(false);
        setMessage("Wysłano zadanie do węzła. Czekam na odpowiedź lidera...");

    };

    const deleteDataToNode = (dataId) => {
        setMessage("");

        if (!selectedNode) {
            setIsError(true);
            setMessage("Proszę wybrać węzeł z listy!");
            return;
        }

        if (!dataId || dataId.toString().trim() === "") {
            setIsError(true);
            setMessage("Proszę wprowadzić id węzła !");
            return;
        }

        if (wsStatus !== "CONNECTED" || !wsRef.current) {
            setIsError(true);
            setMessage("Brak aktywnego połączenia z węzłem!");
            return;
        }

        const taskId = "task_del_" + Date.now();
        const token = localStorage.getItem("access_token");

        const payload = {
            action: "delete_data",
            data: dataId,
            task_id: taskId,
            token: token,
        };

        wsRef.current.send(JSON.stringify(payload));

        setIsError(false);
        setMessage("Wysłano zadanie do węzła. Czekam na odpowiedź lidera...");

    };

    const getDataFromNode = () => {
        setMessage("");

        if (!selectedNode) {
            setIsError(true);
            setMessage("Proszę wybrać węzeł z listy!");
            return;
        }

        if (wsStatus !== "CONNECTED" || !wsRef.current) {
            setIsError(true);
            setMessage("Brak aktywnego połączenia z węzłem!");
            return;
        }

        const taskId = "task_get_" + Date.now();
        const token = localStorage.getItem("access_token");

        const payload = {
            action: "get_data",
            task_id: taskId,
            token: token,
        };

        wsRef.current.send(JSON.stringify(payload));

        setIsError(false);
        //setMessage("Wysłano zadanie do węzła. Czekam na odpowiedź lidera...");
    };

    const clearMessage = () => setMessage("");

    return { wsStatus, message, isError, dataFromNode, sendDataToNode, deleteDataToNode, getDataFromNode, clearMessage };
};