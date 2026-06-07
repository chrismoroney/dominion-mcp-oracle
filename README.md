# Dominion Analytics & MCP Oracle

A real-time, voice-driven state-tracking system and conversational AI for the tabletop game Dominion. This project replaces manual scorekeeping by using an agentic audio pipeline to capture gameplay data, which powers a retrieval-augmented conversational agent (MCP server + Chatbot) to analyze play styles, win rates, and deck-building strategies.

## Important Links
* **Jira Board:** [[Insert your Jira Board URL here](https://moroney-dominion.atlassian.net/jira/software/projects/DOM/boards/1?sprintStarted=true)]
* **Database Dashboard (Neon):** 

## Prerequisites
To run this project locally, you will need:
* Node.js (v20+)
* The Gemini CLI
* Python (v3.10+) 

## Environment Variables
This project requires specific keys to connect to the database and LLM. Create a `.env` file in the root directory and add the following (do not commit this file to version control):

DATABASE_URL="postgresql://[user]:[password]@[endpoint].aws.neon.tech/neondb"
GEMINI_API_KEY="your_google_ai_studio_api_key_here"

## Getting Started
1. Clone the repository.
2. Ensure your `.env` file is populated with the correct keys.
3. Run `npm install` to install dependencies.
4. Run `npm run dev` to start the local development server.