import { useState, useEffect, useRef } from "react";

export const useNodeWebSocket = (selectedNode, nodes, onSuccess) => {
    const [wsStatus, setWsStatus] = useState("DISCONNECTED");
    const [message, setMessage] = useState("");
    const [isError, setIsError] = useState(false);

    const wsRef = useRef(null);

    // KROK 1: Wyciągamy obliczanie URL przed useEffect.
    // Dzięki temu URL zmienia się tylko, gdy faktycznie wybierzemy inny węzeł.
    const foundNode = nodes.find(node => String(node?.node_id) === String(selectedNode));
    const wsUrl = foundNode ? foundNode.url.replace(/^http/, 'ws') + "/ws/client" : null;

    useEffect(() => {
        // Czyszczenie starego połączenia
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        // Jeśli nie mamy URL (bo nic nie wybrano), uciekamy
        if (!wsUrl) {
            setWsStatus("DISCONNECTED");
            return;
        }

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
                // Tutaj wejdzie TYLKO jeśli response.status istnieje i nie jest równy "error"
                setIsError(false);
                setMessage(response.message || "Lider pomyślnie zapisał dane!");
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

        // Cleanup odpala się teraz tylko przy demontażu LUB zmianie wsUrl
        return () => {
            if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
                socket.close();
            }
        };
    }, [wsUrl]); // KROK 2: KRYTYCZNA ZMIANA - zależnością jest TYLKO zmiana URL!

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

    const clearMessage = () => setMessage("");

    return { wsStatus, message, isError, sendDataToNode, deleteDataToNode, clearMessage };
};