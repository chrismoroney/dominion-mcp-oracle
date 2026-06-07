# Dominion Analytics & MCP Oracle

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An advanced, real-time, voice-driven state-tracking system and conversational AI oracle designed for the tabletop deck-building game **Dominion**. 

By replacing tedious manual scorekeeping with an **agentic audio pipeline**, this project captures live gameplay data and feeds a retrieval-augmented conversational agent. It empowers players with an intelligent, real-time "Oracle" capable of analyzing board states, recommending optimal deck-building strategies, and delivering deep post-game analytics.

---

## 🚀 Overview

Playing *Dominion* requires tracking complex combinations, card counts, and deck compositions. **Dominion Analytics & MCP Oracle** takes the cognitive load off players, allowing them to focus entirely on strategy.

Using a microphone to capture verbal gameplay announcements, the system parses natural language into structured game states in real-time. This live database powers a conversational assistant via the **Model Context Protocol (MCP)**, offering strategic insights, card synergy analyses, and play-style tracking.

## 🛠️ System Architecture & Core Features

### 🎙️ 1. Agentic Audio Pipeline
* **Hands-Free Tracking:** Listens to verbal cues during local or remote play (e.g., *"I play Militia, everyone discards down to 3, and I gain 2 Coins"*).
* **NLU State Extraction:** Translates spoken language into concrete database mutations (buys, discards, shuffles, gains, and trash operations).
* **Robust Error Correction:** Automatically reconciles state discrepancies against the official Dominion ruleset.

### 🌐 2. Model Context Protocol (MCP) Integration
* **Standardized Tools:** Integrates as an MCP server, exposing structured capabilities for third-party LLMs or developer tools.
* **State & Rules Retrieval:** Seamlessly queries live board states, player deck statistics, and official card definitions.
* **Strategic Prompts:** Exposes standardized prompts for game setup suggestions, counter-play strategies, and tactical advisories.

### 🧠 3. Conversational Oracle Chatbot
* **Real-Time Strategy Coach:** Ask the Oracle about optimal buy decisions, potential card synergies (e.g., *Engine vs. Big Money*), and counter-picks based on the current Kingdom cards.
* **Retrieval-Augmented Generation (RAG):** Grounded in official rules, card errata, and advanced strategy guides to prevent hallucination.
* **Game History Insights:** Analyzes historical game logs to point out trends in play styles, win rates, and card selection preferences.

---

## 📊 Feature Comparison

| Capability | Manual Scoring | Standard Apps | Dominion MCP Oracle |
| :--- | :---: | :---: | :---: |
| **Real-time Deck Tracking** | ❌ (Mental Math) | ⚠️ (Requires Manual Clicks) |  (Automatic Voice Tracking) |
| **Hands-Free Operation** | ❌ | ❌ |  |
| **Strategy Consultations** | ❌ | ❌ |  (AI-driven RAG Oracle) |
| **MCP Toolset API** | ❌ | ❌ |  |
| **Post-Game Analysis** | ❌ | ⚠️ (Manual Input) |  (Automated Performance Metrics) |

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
