# Swakriti Recommendation Engine

## What This Project Stands For

Swakriti Recommendation Engine is a smart fashion recommendation system designed to help users discover products that match their personal style, preferences, and budget. The platform combines modern web interfaces, AI-driven understanding of user input, and intelligent recommendation logic to create a guided and personalized shopping experience.

## Project Purpose

The goal of this project is to make product discovery easier and more personalized by:

- understanding user preferences through questions and voice input
- interpreting style, occasion, budget, body type, and other attributes
- recommending products that fit the user’s profile
- connecting the recommendation system with ERP data for real product updates

## Main Features

### Frontend Features

- Guided onboarding and questionnaire flow
- Authentication experience
- Voice intake support
- Dynamic question rendering
- Personalized result display
- Session persistence with local storage

### Backend Features

- FastAPI-based API services
- NLP processing for understanding user answers
- Recommendation engine with scoring and filtering
- Search query building for product matching
- ERP webhook integration for live product updates
- Voice token and text-to-speech support

## How the System Works

1. The frontend collects user preferences through questions and voice input.
2. The backend interprets the user responses and builds a recommendation query.
3. The recommendation engine searches and ranks relevant products.
4. The results are returned to the frontend for display to the user.

## Project Structure

- frontend/: React and Vite-based user interface
- backend/: FastAPI backend with NLP, search, scoring, and ERP logic

## Tech Stack

- Frontend: React, Vite, JavaScript, CSS
- Backend: Python, FastAPI
- AI/NLP: Google GenAI and structured parsing
- Integration: ERP webhook support and recommendation search flow

## Summary

Swakriti Recommendation Engine is a full-stack recommendation platform that brings together user experience, intelligent parsing, and personalized product suggestions into one cohesive system.
