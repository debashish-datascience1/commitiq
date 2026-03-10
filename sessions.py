# Simple in-memory session store keyed by phone number
# For production, replace with Redis or a database

sessions = {}


def get_session(phone: str) -> dict:
    if phone not in sessions:
        sessions[phone] = {"state": "idle", "repos": []}
    return sessions[phone]


def set_session(phone: str, **kwargs):
    session = get_session(phone)
    session.update(kwargs)


def clear_session(phone: str):
    sessions[phone] = {"state": "idle", "repos": []}