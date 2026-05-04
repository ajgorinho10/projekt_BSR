from slowapi import Limiter
from slowapi.util import get_remote_address

# Identyfikacja użytkownika na podstawie adresu IP
limiter = Limiter(key_func=get_remote_address)