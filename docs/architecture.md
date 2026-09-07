# Architecture

## Overview
The ERP QA System follows a strict deterministic pipeline where the LLM is only used for semantic parsing, and all data computation is handled by Python/SQLAlchemy executing against a PostgreSQL database.

## Components
1. **API Layer (`app/api`)**: Exposes FastAPI endpoints (`/ask`).
2. **NLQ Pipeline (`app/nlq` & `app/ingestion`)**: Normalizes input, parses query intent into a typed `QueryPlan` via the LLM (using Instructor for structured output), and resolves entities deterministically.
3. **Metric Registry (`app/metrics`)**: Central repository mapping metric requests to specific computation implementations.
4. **Safety & Execution (`app/safety` & `app/query`)**: Validates that a plan is safely executable (Answerability Engine) and executes the registered computation, enforcing that no arbitrary SQL is run. The result is returned as a `ComputedFact`.
5. **Renderer (`app/rendering`)**: Converts structured facts into natural text.
6. **Numeric Guard**: Scans the final output to guarantee no arbitrary numerical hallucinations slip through.

## Trust Boundaries
- **Untrusted**: User input, LLM output, voice transcripts.
- **Trusted**: Database data, registered Python logic, final `ComputedFact`.
- **Enforcement**: LLM is constrained to outputting a `QueryPlan` via Pydantic schemas. The execution engine only executes pre-registered, parameterized SQL via SQLAlchemy. The `NumericGuard` acts as a final fail-safe.
