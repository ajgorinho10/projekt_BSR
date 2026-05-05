from slowapi import Limiter
from slowapi.util import get_remote_address

# Identyfikacja użytkownika na podstawie adresu IP - Limit zapytań
limiter = Limiter(key_func=get_remote_address)