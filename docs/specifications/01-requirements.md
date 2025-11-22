# Requirements Specification

## Overview

This document outlines the functional and non-functional requirements for the Baccarat Predictor Pro application.

## Functional Requirements

### FR1: Prediction Engine
- **FR1.1**: System shall predict next Baccarat outcome (Banker/Player)
- **FR1.2**: System shall calculate confidence level (0-100%)
- **FR1.3**: System shall use multiple algorithms (pattern detection, Bayesian, card counting)

### FR2: Roadmap Generation
- **FR2.1**: System shall generate Big Road
- **FR2.2**: System shall generate Big Eye Boy
- **FR2.3**: System shall generate Small Road
- **FR2.4**: System shall generate Cockroach Pig

### FR3: Card Counting
- **FR3.1**: System shall track running count
- **FR3.2**: System shall calculate true count
- **FR3.3**: System shall use EOR (Effect of Removal) values

### FR4: Statistics
- **FR4.1**: System shall track win/loss statistics
- **FR4.2**: System shall calculate accuracy metrics
- **FR4.3**: System shall display streak information

## Non-Functional Requirements

### NFR1: Performance
- API response time < 100ms
- Roadmap generation < 50ms for 80 hands
- WebSocket latency < 100ms

### NFR2: Scalability
- Support 100+ concurrent users
- Handle 10,000+ simulation shoes

### NFR3: Reliability
- 99.9% uptime
- Graceful error handling
- Data persistence

## Technical Requirements

- Python 3.11+
- Node.js 20+
- PostgreSQL (production) / SQLite (development)
- Redis for caching

