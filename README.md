# Control Server v2

A minimal Flask-based control server for managing and issuing remote commands to registered clients (slaves).

## Features

- Register and track remote clients
- Issue and fetch commands for clients
- Store and retrieve command responses
- Basic authentication using bearer token
- SQLite backend for lightweight storage

## Setup

1. **Install dependencies**

```bash
pip install flask
```
Run the server
```python server.py```
Initialize the database

Visit in your browser or with curl:

GET /v2/init-db

# API Endpoints

All endpoints require the following header:

Authorization: Bearer YOUR_SECRET_TOKEN

##Client Endpoints

    POST /v2/computer-checkin
    Register or update client info

    GET /v2/fetch-orders?slaveName=NAME
    Retrieve pending command

    POST /v2/store-response
    Submit command result

##Operator Endpoints

    POST /v2/send-command
    Send a command to a client

    GET /v2/fetch-response?command_id=ID
    Retrieve a command response

    GET /v2/fetch-slaves
    List all registered clients

###Notes

    Uses SQLite database control_server2.db

    Make sure to set a strong secret token

    Do not expose this server publicly without additional security layers

###License

