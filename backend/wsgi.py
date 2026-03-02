from app import app, init_db

# In produzione con gunicorn, __main__ non gira.
# Quindi inizializziamo qui la tabella/indici al boot.
init_db()
