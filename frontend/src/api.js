import axios from 'axios';

// 1. Tworzymy główną instancję Axios
const api = axios.create({
    // Upewnij się, że ten adres zgadza się z portem Twojego FastAPI!
    baseURL: 'http://localhost:8000', 
    headers: {
        'Content-Type': 'application/json',
    },
});

// 2. Request Interceptor: Zanim wyślesz zapytanie, doklej token
api.interceptors.request.use(
     (config) => {
        const accessToken = localStorage.getItem('access_token');
        
        if (accessToken) {
            config.headers['Authorization'] = `Bearer ${accessToken}`;
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

// 3. Response Interceptor: Co zrobić, gdy backend rzuci błędem? (Magia odświeżania)
api.interceptors.response.use(
    (response) => {
        // Jeśli zapytanie się powiodło (np. 200 OK), po prostu zwracamy dane
        return response;
    },
    async (error) => {

        if (!error || !error.config) {
            console.error("Błąd sieciowy lub blokada CORS:", error);
            return Promise.reject(error);
        }
        // Zapisujemy oryginalne zapytanie, które zakończyło się błędem
        const originalRequest = error.config;

        if (originalRequest.url === '/auth/login' || originalRequest.url === '/auth/verify-2fa') {
        return Promise.reject(error);
    }

        // Jeśli błąd to 401 (Brak autoryzacji) i nie próbowaliśmy go jeszcze ponowić...
        if (error.response?.status === 401 && !originalRequest._retry) {
            
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
                // Wyciągamy refresh_token
                const refreshToken = localStorage.getItem('refresh_token');
                if (!refreshToken) {
                    throw new Error("Brak tokena odświeżającego");
                }

                // Uderzamy do Twojego backendu po nowe tokeny!
                const response = await axios.post('http://localhost:8000/auth/refresh', {
                    refresh_token: refreshToken
                });

                const newAccessToken = response.data.access_token;
                const newRefreshToken = response.data.refresh_token;

                // 1. Zapisujemy NOWE tokeny w przeglądarce
                localStorage.setItem('access_token', newAccessToken);
                localStorage.setItem('refresh_token', newRefreshToken);
                console.log("Zapisuje nowy token");

                // 2. Podmieniamy stary token w oryginalnym zapytaniu na nowy
                originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;

                processQueue(null, newAccessToken);
                // 3. Powtarzamy oryginalne zapytanie (np. do /me lub /admin) z nowym tokenem!
                return api(originalRequest);

            } catch (refreshError) {
                // Jeśli odświeżanie się nie powiodło (np. stary token był na czarnej liście)
                console.error("Sesja wygasła, wylogowywanie...", refreshError);
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/login';
                return Promise.reject(refreshError);
            }finally{
                isRefreshing = false;
            }
        }

        // Jeśli to jakikolwiek inny błąd (np. 400, 403, 500), zwracamy go do komponentu
        return Promise.reject(error);
    }
);

export default api;