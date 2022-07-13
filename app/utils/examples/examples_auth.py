example_AuthorizeValidation = {
    "client_id": "5507cc3a-fd29-11ec-b939-0242ac120002",
    "redirect_uri": "http://localhost:8000",
    "response_type": "code",
    "scope": "API",
    "state": "azerty",
    "code_challenge": "c2cf464b7901205c037cd821bc493b191943bdb5244a665e9fcab6478bf79415",  # hashlib.sha256("AntoineMonBelAntoine".encode()).hexdigest()
    "code_challenge_method": "S256",
    "email": "email@myecl.fr",
    "password": "azerty",
}

example_TokenReq_access_token = {
    "grant_type": "authorization_code",
    "code": "123456789",
    "redirect_uri": "http://localhost:8000/docs",
    "client_id": "5507cc3a-fd29-11ec-b939-0242ac120002",
    "client_secret": "secret",
    "code_verifier": "AntoineMonBelAntoine",
}

example_TokenReq_refresh_token = {
    "grant_type": "refresh_token",
    "refresh_token": "refresh_token",
    "client_id": "5507cc3a-fd29-11ec-b939-0242ac120002",
    "client_secret": "secret",
}
