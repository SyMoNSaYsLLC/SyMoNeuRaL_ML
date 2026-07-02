# warehouse_api_demo

A simple FastAPI warehouse demo built for end-to-end AI testing.

This project includes:

- a **client app** with an HTML form and inventory pages
- a **server API** that manages warehouse inventory
- a **deliberately injected logic flaw** for testing tools like **KaneAI**

The goal is to keep the app simple enough to understand quickly, while still being realistic enough for browser-based and API-based test automation.

## Project Overview

This demo simulates a warehouse ordering workflow.

A user can:

- place an order for a product
- view total warehouse inventory

The system is split into two services:

### Client
The frontend FastAPI app that renders HTML pages and sends requests to the backend API.

### Server
The backend FastAPI API that stores and updates inventory in memory.

## Tech Stack

- Python
- FastAPI
- Jinja2 templates
- Docker
- Docker Compose

## Project Structure

```text
warehouse_api_demo/
├─ client/
│  ├─ client.py
│  ├─ templates/
│  ├─ static/
│  ├─ requirements.txt
│  └─ Dockerfile
├─ server/
│  ├─ server.py
│  ├─ requirements.txt
│  └─ Dockerfile
└─ docker-compose.yml
```