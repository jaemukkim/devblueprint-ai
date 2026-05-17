# DevBlueprint AI

## Project Overview

DevBlueprint AI is an AI-powered system architecture generator.

The goal of this project is to allow users to input a software/service idea in natural language and automatically generate:

- Core feature list
- Recommended tech stack
- REST API specifications
- Database schema suggestions
- Sequence diagrams
- System architecture suggestions

This project is intended as a personal portfolio project focused on:

- AI workflow orchestration
- Backend architecture
- Prompt engineering
- Structured LLM output
- System design automation

---

# Main Goal

Transform:

"service idea"

into:

"developer-ready system blueprint"

using AI.

Example input:

"Sports baseball analysis and prediction service"

Example outputs:

- Feature requirements
- FastAPI API design
- PostgreSQL table design suggestion
- Mermaid sequence diagram
- Recommended AI/ML stack
- Architecture overview

---

# Current Development Scope (MVP)

The MVP should stay simple.

Focus only on:

1. User input
2. LLM analysis
3. Structured JSON generation
4. Result visualization

Do NOT over-engineer early versions.

Avoid:

- Authentication
- Payment systems
- Complex infrastructure
- Kubernetes
- Microservices
- Multi-agent systems initially
- Required database persistence

---

# Recommended Tech Stack

## Backend

- Python
- FastAPI
- Pydantic v2
- Uvicorn

## Frontend

Initially:

- Streamlit

Later upgrade possible:

- React + Vite

## AI

- OpenAI API

## Optional Future Tools

- PostgreSQL
- Redis
- pgvector
- LangGraph
- RAG
- Docker

---

# Expected User Flow

```text
User Input
  -> Requirement Analysis
  -> Feature Extraction
  -> API Specification Generation
  -> Database Schema Suggestion
  -> Sequence Diagram Generation
  -> Final Structured Output
```

---

# Expected API Endpoint

## POST `/api/v1/blueprint/generate`

### Request

```json
{
  "idea": "Sports baseball analysis and prediction service"
}
```

### Response

```json
{
  "overview": "",
  "features": [
    {
      "name": "",
      "description": "",
      "priority": "high | medium | low"
    }
  ],
  "tech_stack": {
    "backend": [],
    "frontend": [],
    "database": [],
    "ai": [],
    "rationale": ""
  },
  "api_spec": [
    {
      "method": "GET | POST | PUT | PATCH | DELETE",
      "path": "",
      "description": "",
      "request": [
        {
          "name": "",
          "type": "",
          "description": "",
          "required": true
        }
      ],
      "response": [
        {
          "name": "",
          "type": "",
          "description": "",
          "required": true
        }
      ]
    }
  ],
  "database_schema": [
    {
      "name": "",
      "description": "",
      "columns": [
        {
          "name": "",
          "type": "",
          "description": "",
          "constraints": []
        }
      ]
    }
  ],
  "sequence_diagram": ""
}
```

---

# Initial Project Structure

```text
backend/
  app/
    api/v1/
      blueprint.py
    core/
      config.py
    schemas/
      blueprint.py
    services/
      blueprint_generator.py
      llm_client.py
      prompts.py
    main.py
frontend/
  streamlit_app.py
docs/
  PROJECT_CONTEXT.md
tests/
  test_blueprint_api.py
```
