# Swakriti Recommendation Engine

## Backend Overview

This backend powers the Swakriti recommendation workflow by combining FastAPI, NLP, search, scoring, and ERP integration to deliver personalized fashion suggestions.

## Backend Features

- FastAPI-based recommendation service with endpoints for live token generation, ERP webhook handling, answer parsing, recommendations, and text-to-speech.
- NLP-driven intake processing to extract user preferences from voice or text responses.
- Query building and recommendation engine integration for personalized product suggestions.
- Scoring and filtering modules for budget, occasion, style, body type, skin tone, fabric, color, and age.
- ERP integration to sync product updates and keep the recommendation index up to date.
- Voice support through live token generation and speech output.
- Vector-based search and recommendation retrieval for matching products to user intent.

## Request Flow

1. The frontend sends user answers or state data to the backend.
2. The backend parses and interprets the incoming information using NLP and rule-based logic.
3. A search query is built from the extracted preferences.
4. The recommendation engine searches the product index and applies scoring and filters.
5. The final recommendations are returned to the frontend for display.

## Main Modules

- app.py: main FastAPI application with API routes and startup logic.
- nlp/: answer extraction, rule engine, taxonomy, and tag extraction.
- search/: query building and recommendation retrieval logic.
- scoring/: attribute-based scoring modules for different profile dimensions.
- erp/: ERP webhook handling and product synchronization.
- voice/: live token generation for voice interactions.
- validation/: validation logic for AI-generated outputs.

## Setup

1. Navigate to the backend folder.
2. Create and activate a virtual environment if needed.
3. Install dependencies with pip install -r requirements.txt.
4. Start the API with python app.py or the appropriate FastAPI run command.

## Tech Stack

- Python
- FastAPI
- Google GenAI / NLP processing
- Vector search and recommendation logic
- ERP webhook integration
