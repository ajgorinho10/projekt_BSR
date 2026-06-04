import axios from 'axios';

let inMemoryAccessToken = null;

export const setAccessToken = (token) => {
    inMemoryAccessToken = token;
};

export const getAccessToken = () =>{
    return inMemoryAccessToken;
};

export const setLogout = async (logout) =>{
    const islogout = await localStorage.setItem("isLogout", logout)
};

export const GetisLogout = async (logout) =>{
    const value = localStorage.getItem("isLogout");

    if(value === "false"){
        return false;
    }

    return true;
}


export const api = axios.create({

    baseURL: 'http://localhost:8000',
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    },
});


api.interceptors.request.use(
     (config) => {   
        if (inMemoryAccessToken) {
            config.headers['Authorization'] = `Bearer ${inMemoryAccessToken}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};


api.interceptors.response.use(
    (response) => {
        return response;
    },
    async (error) => {

        if (!error || !error.config) {
            console.error("Błąd sieciowy lub blokada CORS:", error);
            return Promise.reject(error);
        }
        const originalRequest = error.config;

        if (originalRequest.url === '/auth/login' || originalRequest.url === '/auth/verify-2fa' || originalRequest.url === '/auth/refresh') {
        return Promise.reject(error);
    }

        const isLogout = await GetisLogout();
        if (error.response?.status === 401 && !originalRequest._retry && isLogout == false) {
            
            if (isRefreshing) {
                return new Promise(function(resolve, reject) {
                    failedQueue.push({ resolve, reject });
                }).then(token => {
                    originalRequest.headers['Authorization'] = 'Bearer ' + token;
                    return api(originalRequest);
                }).catch(err => {
                    return Promise.reject(err);
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                const response = await axios.post('http://localhost:8000/auth/refresh', {}, {
                    withCredentials: true 
                });

                inMemoryAccessToken = await response.data.access_token;
                originalRequest.headers['Authorization'] = await `Bearer ${inMemoryAccessToken}`;
                processQueue(null, inMemoryAccessToken);
                return await api(originalRequest);

            } catch (refreshError) {
                console.error("Sesja wygasła, wylogowywanie...", refreshError);
                inMemoryAccessToken = null;
                if (window.location.pathname !== '/login') {
                    window.location.href = '/login';
                }
                return Promise.reject(refreshError);
            }finally{
                isRefreshing = false;
            }
        }

        return Promise.reject(error);
    }
);

export default api;