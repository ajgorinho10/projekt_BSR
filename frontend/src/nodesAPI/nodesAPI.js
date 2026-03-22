
import api from "../api";

export const getAllNodes = async () =>{
    try{
        const reponse = await api.get("http://127.0.0.1:8000/nodes/");
        const data = await reponse.data.nodes;
        
        return data
    }catch(error){
        console.log(error)
        
        return null
    }
};

export const getNodeInfo = async (id) =>{
    try{
        const reponse = await api.get(`http://127.0.0.1:8000/nodes/${id}`);
        const data = await reponse.data;
        
        return data;
    }catch(error){
        console.log(error)
        
        return null
    }
};

export const addNewNode = async(id) =>{
    try{
        console.log(id);
        const reponse = await api.post(`http://127.0.0.1:8000/nodes/${id}`);
        const data = await reponse.data;
        
        return data;
    }catch(error){
        console.log(error)
        
        return null
    }
};

export const KillNode = async(id) =>{
    try{
        const reponse = await api.delete(`http://127.0.0.1:8000/nodes/${id}`);
        const data = await reponse.data;
        
        return data;
    }catch(error){
        console.log(error)
        
        return null
    }
};

export const StopStartNode = async (id,stop) =>{
    try{
        const endpoint = stop ? "deactivate" : "activate";
        const reponse = await api.post(`http://127.0.0.1:8000/nodes/${endpoint}/${id}`);
        
        return reponse.data;
    }catch(error){
        console.log(error)
        
        return null
    }
}