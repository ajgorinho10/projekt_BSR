
import api from "../api";

export const promoteTo= async (role) =>{
    try{
        const reponse = await api.post(`/auth/promote-me?role=${role}`);
        const data = await reponse.data;
        
        return data
    }catch(error){
        console.log(error)
        
        return null
    }
};

export const updateUserPassword = async (pass) =>{
    try{
        const data = {
            password: pass
        }

        const reponse = await api.put(`/auth/update-password`,data);
        
        return reponse.data;
    }catch(error){
        throw error;
    }
};

export const updateUserName = async (name) => {
    try {
        const data = {
            username: name
        }
        const response = await api.put(`/auth/update-username`, data);
        return response.data; 
    } catch (error) {
        throw error; 
    }
};

export const updateUserDisableTOTP = async () =>{
    try{
        const reponse = await api.put(`/auth/update-disable-totp`);
        
        return reponse.data;
    }catch(error){
        throw error;
    }
};

