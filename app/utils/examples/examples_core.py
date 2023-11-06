example_CoreUserUpdate: dict[str, object] = {
    "name": "Backend",
    "firstname": "MyECL",
    "nickname": "Hyperion",
    "birthday": "2022-05-04",
    "promo": 2021,
    "floor": "Adoma",
}

example_CoreUserCreateRequest: dict[str, object] = {
    "email": "user@example.fr",
}


example_CoreBatchUserCreateRequest: dict[str, object] = {
    "email": "user@example.fr",
    "account_type": "39691052-2ae5-4e12-99d0-7a9f5f2b0136",
}


example_CoreUserActivateRequest: dict[str, object] = {
    "name": "Name",
    "firstname": "Firstname",
    "nickname": "Antoine",
    "activation_token": "62D-QJI5IYrjuywH8IWnuBo0xHrbTCfw_18HP4mdRrA",
    "password": "areallycomplexpassword",
    "floor": "Autre",
}
