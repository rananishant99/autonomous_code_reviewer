# utils/encryption.py

from cryptography.fernet import Fernet
from django.conf import settings


def get_fernet():
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_token(plain_text_token: str) -> str:
    fernet = get_fernet()
    encrypted = fernet.encrypt(plain_text_token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_token.encode())
    return decrypted.decode()
