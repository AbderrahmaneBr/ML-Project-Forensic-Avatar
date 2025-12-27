# Backend - AI Forensic Avatar API

FastAPI backend for the AI Forensic Avatar application. Provides image analysis, object detection, OCR, and AI-powered forensic hypothesis generation with streaming responses.

## Table of Contents

- [Overview](#overview)
- [Glossary](#glossary)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Core Concepts](#core-concepts)
- [API Reference](#api-reference)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [Services Deep Dive](#services-deep-dive)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Docker](#docker)
- [Testing](#testing)

---

## Overview

The backend serves as the brain of the AI Forensic Avatar application. It processes crime scene images through a multi-stage AI pipeline:

1. **Image Upload** → Store images in MinIO object storage
2. **Object Detection** → Identify objects using YOLOv8
3. **Text Extraction** → Extract text using Tesseract OCR
4. **Hypothesis Generation** → Generate forensic analysis using Ollama LLM
5. **Streaming Response** → Stream results to frontend via SSE

---

## Glossary

This section explains all technical terms, acronyms, and concepts used throughout this documentation.

### Networking & Protocols

| Term | Full Name | Explanation |
|------|-----------|-------------|
| **API** | Application Programming Interface | A set of rules that allows different software applications to communicate. Our backend exposes a REST API that the frontend calls to send/receive data. |
| **REST** | Representational State Transfer | An architectural style for APIs using standard HTTP methods (GET, POST, PUT, DELETE) to perform operations on resources. |
| **HTTP** | HyperText Transfer Protocol | The foundation protocol for data communication on the web. Defines how messages are formatted and transmitted. |
| **SSE** | Server-Sent Events | A technology where the server can push data to the client over a single HTTP connection. Unlike WebSockets (bidirectional), SSE is unidirectional (server → client). Perfect for streaming LLM tokens in real-time. |
| **WebSocket** | - | A protocol for full-duplex (two-way) communication over a single TCP connection. We use SSE instead because we only need server-to-client streaming. |
| **Endpoint** | - | A specific URL path that accepts requests. Example: `/api/v1/conversations` is an endpoint for managing conversations. |

### Data Formats & Validation

| Term | Full Name | Explanation |
|------|-----------|-------------|
| **JSON** | JavaScript Object Notation | A lightweight data format for storing and transporting data. Looks like: `{"name": "value"}`. All our API requests/responses use JSON. |
| **UUID** | Universally Unique Identifier | A 128-bit identifier guaranteed to be unique. Example: `550e8400-e29b-41d4-a716-446655440000`. We use UUIDs for all database IDs. |
| **Pydantic** | - | A Python library for data validation using type annotations. Automatically validates request bodies and generates error messages. |
| **Schema** | - | A definition of data structure. Pydantic schemas define what fields a request/response should have and their types. |

### Database Concepts

| Term | Full Name | Explanation |
|------|-----------|-------------|
| **ORM** | Object-Relational Mapping | A technique that lets you query and manipulate database data using object-oriented code instead of SQL. SQLAlchemy is our ORM. |
| **SQL** | Structured Query Language | The standard language for interacting with relational databases. Example: `SELECT * FROM users`. |
| **CRUD** | Create, Read, Update, Delete | The four basic operations for persistent storage. Our conversation endpoints implement full CRUD. |
| **PK** | Primary Key | A unique identifier for each row in a database table. Cannot be null or duplicated. |
| **FK** | Foreign Key | A field that links to the primary key of another table, creating a relationship between tables. |
| **ACID** | Atomicity, Consistency, Isolation, Durability | Properties that guarantee database transactions are processed reliably. PostgreSQL is ACID-compliant. |

### Machine Learning & AI

| Term | Full Name | Explanation |
|------|-----------|-------------|
| **LLM** | Large Language Model | An AI model trained on massive text datasets to understand and generate human-like text. Examples: GPT-4, LLaMA, Claude. We use llama3.2 via Ollama. |
| **OCR** | Optical Character Recognition | Technology that converts images of text into machine-readable text. Tesseract reads text from crime scene photos. |
| **YOLO** | You Only Look Once | A real-time object detection algorithm. YOLOv8 identifies objects (person, knife, car) in images in a single forward pass. |
| **Inference** | - | The process of using a trained model to make predictions on new data. When Ollama generates text, it's performing inference. |
| **Token** | - | The smallest unit of text processed by an LLM. Can be a word, part of a word, or punctuation. "Hello world" = 2 tokens. |
| **Streaming** | - | Sending data piece by piece as it becomes available, rather than waiting for the complete response. LLMs stream tokens as they're generated. |
| **Confidence Score** | - | A number (0-1) indicating how certain the model is about its prediction. 0.92 = 92% confident. |
| **Bounding Box (bbox)** | - | Coordinates `[x1, y1, x2, y2]` defining a rectangle around a detected object in an image. |

### Infrastructure & DevOps

| Term | Full Name | Explanation |
|------|-----------|-------------|
| **Docker** | - | A platform for running applications in isolated containers. Each container packages code + dependencies, ensuring consistent environments. |
| **Container** | - | A lightweight, standalone package containing everything needed to run software: code, runtime, libraries, settings. |
| **Docker Compose** | - | A tool for defining and running multi-container applications. Our `docker-compose.yml` defines 5 services that work together. |
| **Image (Docker)** | - | A read-only template used to create containers. Built from a Dockerfile. |
| **Volume** | - | Persistent storage for Docker containers. Data in volumes survives container restarts. |
| **S3** | Simple Storage Service | Amazon's object storage service. MinIO is S3-compatible, meaning it uses the same API. |
| **Object Storage** | - | Storage for unstructured data (files, images, videos) accessed via HTTP. Unlike file systems, no folder hierarchy is required. |

### Python & FastAPI

| Term | Full Name | Explanation |
|------|-----------|-------------|
| **FastAPI** | - | A modern Python web framework for building APIs. Features automatic docs, type validation, and async support. |
| **Async/Await** | Asynchronous | A programming pattern that allows non-blocking operations. While waiting for a database query, the server can handle other requests. |
| **Router** | - | A FastAPI component that groups related endpoints. We have routers for conversations, upload, detect, etc. |
| **Dependency Injection** | - | A pattern where components receive their dependencies from external sources. FastAPI uses this for database sessions, authentication, etc. |
| **Lifespan** | - | FastAPI's mechanism for running code at application startup/shutdown. We use it to create database tables on startup. |
| **Middleware** | - | Code that runs before/after every request. Used for logging, CORS, authentication, etc. |

### Architecture Patterns

| Term | Full Name | Explanation |
|------|-----------|-------------|
| **Service Layer** | - | A design pattern that encapsulates business logic in dedicated service classes. Keeps API routes thin and logic reusable. |
| **Repository Pattern** | - | A pattern that abstracts data access logic. Our ORM models serve this purpose. |
| **Pipeline** | - | A series of processing steps where output of one step feeds into the next. Our AI pipeline: Upload → Detect → OCR → LLM. |
| **Microservices** | - | An architecture where an application is built as a collection of loosely coupled services. Each Docker service (postgres, minio, ollama) is a microservice. |

### Specific Technologies

| Term | Explanation |
|------|-------------|
| **PostgreSQL** | An open-source relational database. Stores conversations, messages, and image metadata in structured tables with relationships. |
| **MinIO** | An open-source object storage server compatible with Amazon S3 API. Stores actual image files (JPG, PNG) separately from the database. |
| **Ollama** | A tool for running LLMs locally. Provides an API to interact with models like llama3.2 without cloud dependencies. |
| **Tesseract** | An open-source OCR engine originally developed by HP, now maintained by Google. Reads text from images. |
| **SQLAlchemy** | Python's most popular ORM. Lets you define database tables as Python classes and query using Python methods. |
| **Pydantic** | Data validation library using Python type hints. Ensures API requests have correct structure and types. |
| **Uvicorn** | An ASGI server that runs FastAPI applications. Handles incoming HTTP requests and passes them to FastAPI. |
| **ASGI** | Asynchronous Server Gateway Interface - A standard interface between async Python web servers and applications. |

### File Formats

| Term | Explanation |
|------|-------------|
| **YAML** | A human-readable data format used for configuration files. `docker-compose.yml` uses YAML syntax. |
| **Dockerfile** | A text file containing instructions to build a Docker image. Each line is a build step. |
| **Requirements.txt** | A file listing Python package dependencies. `pip install -r requirements.txt` installs them all. |

### Common HTTP Status Codes

| Code | Meaning | When It's Used |
|------|---------|----------------|
| **200** | OK | Request succeeded |
| **201** | Created | Resource was created (e.g., new conversation) |
| **204** | No Content | Success but nothing to return (e.g., delete) |
| **400** | Bad Request | Client sent invalid data |
| **404** | Not Found | Resource doesn't exist |
| **422** | Unprocessable Entity | Validation error (Pydantic) |
| **500** | Internal Server Error | Something broke on the server |

---

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
│                         http://localhost:3000                                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ HTTP/SSE
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NGINX REVERSE PROXY                                │
│                    Routes /api/* to FastAPI backend                          │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                                     │
│                       http://localhost:8000                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Upload    │  │   Detect    │  │     OCR     │  │   Analyze   │        │
│  │   Router    │  │   Router    │  │   Router    │  │   Router    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         ▼                ▼                ▼                ▼                │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                        SERVICE LAYER                             │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │       │
│  │  │ Storage  │  │Detection │  │   OCR    │  │   NLP    │        │       │
│  │  │ Service  │  │ Service  │  │ Service  │  │ Service  │        │       │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │       │
│  └───────┼─────────────┼─────────────┼─────────────┼───────────────┘       │
└──────────┼─────────────┼─────────────┼─────────────┼────────────────────────┘
           │             │             │             │
           ▼             ▼             ▼             ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    MinIO     │  │   YOLOv8     │  │  Tesseract   │  │   Ollama     │
│   (S3-like)  │  │   (PyTorch)  │  │    (OCR)     │  │  (llama3.2)  │
│  :9000/:9001 │  │   In-memory  │  │   In-memory  │  │    :11434    │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
                                                              │
           ┌──────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            POSTGRESQL DATABASE                                │
│                              :5432                                            │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│   │  conversations  │───▶│    messages     │───▶│     images      │         │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow Diagram

```
User uploads image and sends message
              │
              ▼
┌─────────────────────────────────────┐
│     POST /api/v1/upload             │
│     ─────────────────────           │
│     • Validate image format         │
│     • Generate unique filename      │
│     • Upload to MinIO bucket        │
│     • Return image URL              │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  POST /api/v1/conversations/{id}/   │
│  chat                               │
│  ───────────────────────────────    │
│  Request Body:                      │
│  {                                  │
│    "content": "Analyze this scene", │
│    "image_ids": ["uuid-1", "uuid-2"]│
│  }                                  │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│         AI PIPELINE                 │
│  ┌───────────────────────────────┐  │
│  │ 1. Fetch images from MinIO    │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │ 2. Run YOLOv8 Detection       │  │
│  │    • person (0.92)            │  │
│  │    • knife (0.87)             │  │
│  │    • car (0.78)               │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │ 3. Run Tesseract OCR          │  │
│  │    • "EVIDENCE TAG #4521"     │  │
│  │    • "DO NOT CROSS"           │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │ 4. Generate LLM Hypothesis    │  │
│  │    Ollama streams tokens...   │──┼──▶ SSE to Frontend
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## Tech Stack

| Technology | Purpose | Why We Use It |
|------------|---------|---------------|
| **FastAPI** | Web framework | Async support, automatic OpenAPI docs, type validation |
| **PostgreSQL** | Relational database | ACID compliance, complex queries, reliable storage |
| **MinIO** | Object storage | S3-compatible, self-hosted, handles large binary files |
| **Ollama** | LLM inference | Local execution, no API costs, privacy-preserving |
| **YOLOv8** | Object detection | State-of-the-art accuracy, fast inference |
| **Tesseract** | OCR | Open-source, supports multiple languages |
| **SQLAlchemy** | ORM | Pythonic database operations, migration support |
| **SSE-Starlette** | Streaming | Real-time token streaming to frontend |

---

## Project Structure

```
backend/
├── api/                      # API Layer - HTTP route handlers
│   ├── analyze.py            # Full analysis pipeline endpoint
│   ├── chat.py               # Streaming chat with SSE
│   ├── conversation.py       # CRUD for conversations
│   ├── detect.py             # Object detection endpoint
│   ├── jobs.py               # Background job status tracking
│   ├── ocr.py                # Text extraction endpoint
│   └── upload.py             # Image upload to MinIO
│
├── core/                     # Core Business Logic
│   └── ai_pipeline.py        # Orchestrates the full AI pipeline
│
├── db/                       # Database Layer
│   ├── database.py           # SQLAlchemy engine & session setup
│   └── models.py             # ORM models (Conversation, Message, Image)
│
├── schemas/                  # Pydantic Schemas
│   ├── conversation.py       # Request/Response models
│   └── message.py            # Message validation schemas
│
├── services/                 # Service Layer - Business Logic
│   ├── chat_service.py       # Chat orchestration & streaming
│   ├── detection_service.py  # YOLOv8 wrapper
│   ├── nlp_service.py        # Ollama LLM integration
│   ├── ocr_service.py        # Tesseract OCR wrapper
│   └── storage_service.py    # MinIO operations
│
├── tests/                    # Test Suite
│   ├── conftest.py           # Pytest fixtures
│   └── test_services.py      # Service unit tests
│
├── main.py                   # FastAPI application entrypoint
├── config.py                 # Environment configuration
└── Dockerfile                # Container definition
```

### Layer Responsibilities

```
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER (api/)                        │
│  • HTTP request/response handling                            │
│  • Input validation (Pydantic)                               │
│  • Route definitions                                         │
│  • Error responses                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   SERVICE LAYER (services/)                  │
│  • Business logic implementation                             │
│  • External service integration                              │
│  • Data transformation                                       │
│  • No HTTP awareness                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER (db/)                          │
│  • Database models (SQLAlchemy ORM)                          │
│  • Query operations                                          │
│  • Connection management                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### 1. Conversations & Messages

The application uses a chat-based interface where each **Conversation** contains multiple **Messages**.

```
Conversation (Case File)
├── Message 1 (User: "Analyze this crime scene")
│   └── Images: [crime_scene_01.jpg, crime_scene_02.jpg]
├── Message 2 (Assistant: "The scene reveals...")
├── Message 3 (User: "What about the weapon?")
└── Message 4 (Assistant: "Upon closer inspection...")
```

### 2. AI Pipeline

The AI pipeline processes images through multiple stages:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   IMAGE     │───▶│   YOLO      │───▶│  TESSERACT  │───▶│   OLLAMA    │
│   INPUT     │    │  DETECTION  │    │     OCR     │    │     LLM     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                          │                  │                  │
                          ▼                  ▼                  ▼
                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                   │  Objects:   │    │   Text:     │    │ Hypothesis: │
                   │  - person   │    │  "EVIDENCE  │    │ "The scene  │
                   │  - knife    │    │   #4521"    │    │  suggests..." │
                   │  - blood    │    │             │    │             │
                   └─────────────┘    └─────────────┘    └─────────────┘
```

### 3. Confidence Levels

Detection results include confidence scores that influence the LLM's language:

| Confidence | Label | LLM Language Example |
|------------|-------|---------------------|
| ≥ 0.80 | `[HIGH]` | "clearly visible", "unmistakably present" |
| 0.50 - 0.79 | `[MEDIUM]` | "appears to be", "likely indicates" |
| < 0.50 | `[LOW]` | "possibly", "faintly resembles" |

### 4. Server-Sent Events (SSE)

The chat endpoint uses SSE for real-time streaming:

```
Client                                    Server
  │                                          │
  │──── POST /chat ─────────────────────────▶│
  │                                          │
  │◀──── event: token ───────────────────────│  "The"
  │◀──── event: token ───────────────────────│  " scene"
  │◀──── event: token ───────────────────────│  " reveals"
  │◀──── event: token ───────────────────────│  "..."
  │◀──── event: done ────────────────────────│
  │                                          │
```

---

## API Reference

### Conversations

#### List Conversations
```http
GET /api/v1/conversations
```
Returns all conversations with their associated images.

#### Create Conversation
```http
POST /api/v1/conversations
Content-Type: application/json

{
  "name": "Case #2024-001"
}
```

#### Get Conversation
```http
GET /api/v1/conversations/{id}
```

#### Update Conversation
```http
PATCH /api/v1/conversations/{id}
Content-Type: application/json

{
  "name": "Updated Case Name"
}
```

#### Delete Conversation
```http
DELETE /api/v1/conversations/{id}
```

#### Get Messages
```http
GET /api/v1/conversations/{id}/messages
```

### Chat (Streaming)

#### Send Message & Stream Response
```http
POST /api/v1/conversations/{id}/chat
Content-Type: application/json

{
  "content": "Analyze the evidence in these images",
  "image_ids": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

**Response** (SSE Stream):
```
event: token
data: {"token": "The"}

event: token
data: {"token": " forensic"}

event: token
data: {"token": " evidence"}

event: done
data: {"message_id": "uuid", "content": "The forensic evidence..."}
```

### Image Processing

#### Upload Image
```http
POST /api/v1/upload
Content-Type: multipart/form-data

file: <binary image data>
conversation_id: "uuid"
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "crime_scene.jpg",
  "url": "http://minio:9000/forensic/uuid/crime_scene.jpg",
  "status": "uploaded"
}
```

#### Object Detection
```http
POST /api/v1/detect
Content-Type: application/json

{
  "image_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response**:
```json
{
  "objects": [
    {"label": "person", "confidence": 0.92, "bbox": [100, 150, 300, 400]},
    {"label": "knife", "confidence": 0.87, "bbox": [450, 200, 520, 280]}
  ]
}
```

#### OCR Text Extraction
```http
POST /api/v1/ocr
Content-Type: application/json

{
  "image_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response**:
```json
{
  "texts": [
    {"text": "EVIDENCE TAG #4521", "confidence": 0.95},
    {"text": "POLICE LINE DO NOT CROSS", "confidence": 0.88}
  ]
}
```

#### Full Analysis Pipeline
```http
POST /api/v1/analyze
Content-Type: application/json

{
  "image_ids": ["uuid-1", "uuid-2"],
  "context": "Suspected robbery scene"
}
```

---

## Data Flow

### Complete Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTION                                   │
│                                                                              │
│  1. User uploads image(s)                                                   │
│  2. User types message: "What happened here?"                               │
│  3. User clicks Send                                                        │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND → BACKEND                                 │
│                                                                              │
│  POST /api/v1/conversations/{id}/chat                                       │
│  {                                                                           │
│    "content": "What happened here?",                                        │
│    "image_ids": ["abc-123", "def-456"]                                      │
│  }                                                                           │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CHAT SERVICE                                       │
│                                                                              │
│  1. Save user message to database                                           │
│  2. Fetch image URLs from MinIO                                             │
│  3. Start AI pipeline                                                        │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
           ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
           │  DETECTION   │  │     OCR      │  │   CONTEXT    │
           │   SERVICE    │  │   SERVICE    │  │  (user msg)  │
           │              │  │              │  │              │
           │ YOLOv8 model │  │  Tesseract   │  │   "What      │
           │ ───────────  │  │ ───────────  │  │   happened   │
           │ person: 0.92 │  │ "EVIDENCE"   │  │   here?"     │
           │ knife: 0.87  │  │ "#4521"      │  │              │
           └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                  │                 │                 │
                  └─────────────────┼─────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NLP SERVICE                                        │
│                                                                              │
│  Prompt to Ollama (llama3.2):                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ SYSTEM: You are a forensic analyst providing crime scene analysis...  │ │
│  │                                                                        │ │
│  │ USER: Analyze this crime scene evidence:                              │ │
│  │                                                                        │ │
│  │ Objects at scene: [HIGH] person, [HIGH] knife                         │ │
│  │ Text found: [HIGH] "EVIDENCE #4521"                                   │ │
│  │                                                                        │ │
│  │ Context: What happened here?                                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Ollama generates tokens...                                                  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      │ Streaming tokens
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SSE RESPONSE                                       │
│                                                                              │
│  event: token                                                                │
│  data: {"token": "The"}                                                     │
│                                                                              │
│  event: token                                                                │
│  data: {"token": " scene"}                                                  │
│                                                                              │
│  event: token                                                                │
│  data: {"token": " reveals"}                                                │
│  ...                                                                         │
│                                                                              │
│  event: done                                                                 │
│  data: {"message_id": "xyz-789", "content": "The scene reveals..."}         │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE UPDATE                                    │
│                                                                              │
│  INSERT INTO messages (conversation_id, role, content)                      │
│  VALUES ('conv-123', 'assistant', 'The scene reveals...')                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE SCHEMA                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│    conversations    │       │      messages       │       │       images        │
├─────────────────────┤       ├─────────────────────┤       ├─────────────────────┤
│ id (PK, UUID)       │──┐    │ id (PK, UUID)       │──┐    │ id (PK, UUID)       │
│ name (VARCHAR)      │  │    │ conversation_id (FK)│◀─┘    │ message_id (FK)     │◀─┐
│ created_at (TIMESTAMP) │    │ role (ENUM)         │       │ filename (VARCHAR)  │  │
│ updated_at (TIMESTAMP) │    │ content (TEXT)      │       │ url (VARCHAR)       │  │
└─────────────────────┘  │    │ created_at          │───────│ status (VARCHAR)    │  │
                         │    └─────────────────────┘       │ created_at          │  │
                         │              │                   └─────────────────────┘  │
                         │              │                                            │
                         └──────────────┴────────────────────────────────────────────┘

RELATIONSHIPS:
─────────────────────────────────────────────────────────────────────────────────────

conversations  1 ────────────────────────────────────────────────────────── N  messages
               │  "A conversation has many messages"                         │
               │                                                             │
               └─────────────────────────────────────────────────────────────┘

messages       1 ────────────────────────────────────────────────────────── N  images
               │  "A message can have many attached images"                  │
               │                                                             │
               └─────────────────────────────────────────────────────────────┘
```

### Table Definitions

```sql
-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Images table
CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Services Deep Dive

### Detection Service (YOLOv8)

```python
# How YOLOv8 object detection works

Input Image (crime_scene.jpg)
         │
         ▼
┌─────────────────────────────────────┐
│         YOLOv8 Model                │
│  ┌───────────────────────────────┐  │
│  │ 1. Image Preprocessing        │  │
│  │    • Resize to 640x640        │  │
│  │    • Normalize pixel values   │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │ 2. Neural Network Forward     │  │
│  │    • Backbone (feature ext)   │  │
│  │    • Neck (feature fusion)    │  │
│  │    • Head (detection)         │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │ 3. Post-processing            │  │
│  │    • Non-max suppression      │  │
│  │    • Confidence thresholding  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         │
         ▼
Output: [
  {label: "person", confidence: 0.92, bbox: [x1, y1, x2, y2]},
  {label: "knife", confidence: 0.87, bbox: [x1, y1, x2, y2]}
]
```

### OCR Service (Tesseract)

```python
# How Tesseract OCR works

Input Image (evidence_tag.jpg)
         │
         ▼
┌─────────────────────────────────────┐
│       Tesseract OCR Engine          │
│  ┌───────────────────────────────┐  │
│  │ 1. Image Preprocessing        │  │
│  │    • Binarization             │  │
│  │    • Deskewing                │  │
│  │    • Noise removal            │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │ 2. Text Detection             │  │
│  │    • Line detection           │  │
│  │    • Word segmentation        │  │
│  │    • Character segmentation   │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │ 3. Character Recognition      │  │
│  │    • LSTM neural network      │  │
│  │    • Language model           │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         │
         ▼
Output: [
  {text: "EVIDENCE TAG #4521", confidence: 0.95},
  {text: "POLICE LINE", confidence: 0.88}
]
```

### NLP Service (Ollama)

```python
# How the LLM generates forensic hypotheses

┌─────────────────────────────────────────────────────────────────────────────┐
│                        NLP SERVICE FLOW                                      │
└─────────────────────────────────────────────────────────────────────────────┘

Inputs:
├── detected_objects: [{label: "person", confidence: 0.92}, ...]
├── extracted_texts: [{text: "EVIDENCE #4521", confidence: 0.95}, ...]
└── user_context: "What happened here?"
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PROMPT CONSTRUCTION                                     │
│                                                                              │
│  SYSTEM PROMPT:                                                              │
│  "You are a forensic analyst providing crime scene analysis...              │
│   Use dramatic, detective-noir narration style...                           │
│   Adjust certainty based on confidence: [HIGH], [MEDIUM], [LOW]..."         │
│                                                                              │
│  USER PROMPT:                                                                │
│  "Analyze this crime scene evidence:                                        │
│                                                                              │
│   Objects at scene: [HIGH] person, [HIGH] knife, [MEDIUM] blood stain       │
│   Text found: [HIGH] 'EVIDENCE TAG #4521'                                   │
│                                                                              │
│   Additional Context: What happened here?"                                  │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      OLLAMA (llama3.2)                                       │
│                                                                              │
│  • Loads model into GPU/CPU memory                                          │
│  • Processes prompt through transformer layers                              │
│  • Generates tokens autoregressively                                        │
│  • Streams each token as it's generated                                     │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼ (streaming)
┌─────────────────────────────────────────────────────────────────────────────┐
│                      OUTPUT (token by token)                                 │
│                                                                              │
│  "The" → " scene" → " before" → " us" → " tells" → " a" → " chilling" →    │
│  " tale" → "." → " The" → " knife" → "," → " unmistakably" → " present"    │
│  → "," → " bears" → " witness" → " to" → " violence" → "..." → [END]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `POSTGRES_HOST` | PostgreSQL hostname | `localhost` | Yes |
| `POSTGRES_PORT` | PostgreSQL port | `5432` | No |
| `POSTGRES_USER` | Database username | `user` | Yes |
| `POSTGRES_PASSWORD` | Database password | `admin` | Yes |
| `POSTGRES_DB` | Database name | `forensic_db` | Yes |
| `MINIO_ENDPOINT` | MinIO server endpoint | `localhost:9000` | Yes |
| `MINIO_ACCESS_KEY` | MinIO access key | `minioadmin` | Yes |
| `MINIO_SECRET_KEY` | MinIO secret key | `minioadmin` | Yes |
| `MINIO_BUCKET` | Storage bucket name | `forensic` | No |
| `MINIO_SECURE` | Use HTTPS for MinIO | `false` | No |
| `OLLAMA_HOST` | Ollama API endpoint | `http://localhost:11434` | Yes |
| `OLLAMA_MODEL` | LLM model to use | `llama3.2` | No |

---

## Local Development

### Prerequisites

1. **Python 3.11+**
2. **Tesseract OCR**
   ```bash
   # macOS
   brew install tesseract

   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr

   # Windows
   # Download installer from https://github.com/UB-Mannheim/tesseract/wiki
   ```

3. **PostgreSQL** (or use Docker)
4. **MinIO** (or use Docker)
5. **Ollama** with llama3.2 model
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh

   # Pull the model
   ollama pull llama3.2
   ```

### Setup

```bash
# Clone and navigate to project
cd ML-Project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start dependencies (if using Docker)
docker-compose up -d postgres minio ollama

# Run the development server
fastapi dev backend/main.py
```

### Development Server

```bash
# With auto-reload (recommended for development)
fastapi dev backend/main.py

# Production mode
fastapi run backend/main.py --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Docker

### Build & Run

```bash
# Build and start all services
docker-compose up --build

# Start only backend and dependencies
docker-compose up --build fastapi postgres minio ollama

# View logs
docker-compose logs -f fastapi
```

### Docker Compose Services

```yaml
services:
  fastapi:      # Backend API (port 8000)
  postgres:     # Database (port 5432)
  minio:        # Object storage (ports 9000, 9001)
  ollama:       # LLM inference (port 11434)
  frontend:     # React app (port 3000)
```

---

## Testing

### Run Tests

```bash
# Run all tests
pytest backend/tests -v

# Run with coverage
pytest backend/tests -v --cov=backend

# Run specific test file
pytest backend/tests/test_services.py -v

# Run specific test
pytest backend/tests/test_services.py::test_detection_service -v
```

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_services.py     # Service unit tests
├── test_api.py          # API integration tests
└── test_pipeline.py     # End-to-end pipeline tests
```

### Example Test

```python
import pytest
from backend.services.detection_service import detect_objects

def test_detection_returns_objects():
    # Arrange
    image_path = "tests/fixtures/test_image.jpg"

    # Act
    results = detect_objects(image_path)

    # Assert
    assert isinstance(results, list)
    assert all("label" in obj for obj in results)
    assert all("confidence" in obj for obj in results)
```
