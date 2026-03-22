import React,{useState,useEffect} from "react";
import { useNodes } from "../context/NodesContext";
import { addNewNode,KillNode } from "../nodesAPI/nodesAPI";
import { StopStartNode } from "../nodesAPI/nodesAPI";

export const AdminPanel = () =>{
    const {nodes,nodesInfo} = useNodes();

    const [inputValue, setInputValue] = useState(1);


    const addNodeButton = () =>{
        const finalValue = inputValue === '' ? 1 : inputValue;
        addNewNode(finalValue);
    }

    const KillNodeButton = (id) =>{
        KillNode(id);
    };

    const handleInputChange = (e) => {
        const value = e.target.value;

        if (value === '') {
            setInputValue('');
            return;
        }

        const parsedValue = parseInt(value, 10);
1
        if (!isNaN(parsedValue) && parsedValue >= 1) {
            setInputValue(parsedValue);
        }
    };

    return(
        <div>
            <p>Aktywne węzły: {nodes?.length || 0}</p>
            <input 
                    type="number" 
                    min="1"
                    value={inputValue} 
                    onChange={handleInputChange}
                    style={{ marginLeft: '10px', width: '60px' }}
                />
            <button onClick={addNodeButton}>Dodaj wątek</button>
            {nodes && nodes.map((node)=>{
                const id = node?.node_id;
                const nodeDetail = nodesInfo?.[id];

                const leader_id = nodeDetail?.leader_id || "Brak";
                const process_status = node?.status;
                const node_status = nodeDetail?.status || "NOT ACTIVE";

                const running = node_status === "ACTIVE" ? true : false

                return(
                    <div key={id}>
                        <p>id:{id}</p>
                        <p>Leader ID:{leader_id}</p>
                        <p>Status procesu: {process_status}</p>
                        <p>Status wątku: {node_status}</p>
                        <button onClick={()=>StopStartNode(id,running)}>{running == true ? "Zatrzymaj process" : "Wznów process"}</button>
                        <button onClick={()=>KillNodeButton(id)}>Zabij process</button>
                    </div>
                );

            })}
        </div>
    );
};