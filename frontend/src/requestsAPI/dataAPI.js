import axios from "axios";
import api from "../api.js";

const dataApi = axios.create({
    headers: {
        'Content-Type': 'application/json',
    },
});

dataApi.interceptors.request.use(
    (config) => {
        const accessToken = localStorage.getItem('access_token');
        if (accessToken) {
            config.params = { ...config.params, token: accessToken };
        }
        return config;
    },
    (error) => Promise.reject(error)
);

dataApi.interceptors.response.use(
    (response) => {
        return response;
    },
    async (error) => {
        const originalRequest = error.config;

        if (error.response && (error.response.status === 401 || error.response.status === 403) && !originalRequest._retry) {
            originalRequest._retry = true;

            try {

                await api.get("/auth/me");

                const newAccessToken = localStorage.getItem('access_token');
                originalRequest.params.token = newAccessToken;

                return dataApi(originalRequest);

            } catch (refreshError) {
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);


export const sendData = async (path,dataToSend) =>{
    try{
        const response = await dataApi.post(`${path}/data`,{data:dataToSend})

        return response.data;
    }catch(error){
        throw error
    }
};
