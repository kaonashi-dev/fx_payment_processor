# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FX Payment Processor is a multi-currency wallet system API built with FastAPI, supporting USD and MXN currencies with dynamic foreign exchange rates. The system provides wallet operations (fund, convert, withdraw) with complete transaction tracking and structured logging.

## Technology Stack

- **Language**: Python 3.13+
- **Web Framework**: FastAPI with uvicorn
- **Database**: PostgreSQL 15 with SQLModel (SQLAlchemy + Pydantic)
- **Migrations**: Alembic
- **Package Manager**: uv
- **Scheduling**: APScheduler for dynamic FX rate updates
- **Logging**: structlog with JSON formatting
- **Containerization**: Docker with docker-compose

## Development Commands

```bash
# Local development
make install          # Install dependencies with uv
make dev              # Run development server at localhost:3700 with hot reload
make run              # Run directly with Python module execution
make test             # Run pytest tests
make clean            # Clean cache and temporary files

# Docker development
make docker-build     # Build Docker containers
make docker-up        # Start containers
make docker-down      # Stop containers

# Database
make db-migrate       # Run Alembic migrations (upgrade to head)
make db-seed          # Seed database with test data via scripts/seed_db.py

# Quick start everything (Docker + DB setup)
make run              # Combined: build + up + migrate + seed
```

**Note**: The API is accessible at `http://localhost:3700` (local) or `http://localhost:3700` (Docker), with interactive docs at `/docs`.

## Architecture Overview

### Layered Architecture

The codebase follows a clean layered architecture:

```
src/
├── main.py                    # FastAPI app with lifespan management
├── config/                    # Application configuration
│   ├── config.py             # Settings with pydantic-settings
│   └── logging_config.py     # structlog setup
├── models/                    # SQLModel database models
│   ├── wallet.py             # Wallet with unique (user_id, currency) constraint
│   ├── transaction.py        # Transaction with type-specific fields
│   └── currency.py           # Currency enum (USD, MXN)
├── repositories/              # Data access layer
│   ├── wallet_repository.py  # CRUD for wallets
│   └── transaction_repository.py  # CRUD for transactions
├── services/                  # Business logic layer
│   ├── wallet_service.py     # Wallet operations (fund, convert, withdraw)
│   └── fx_rates.py           # FX rate management with scheduler
├── schemas/                   # Pydantic request/response models
│   └── wallet.py             # API contracts
├── api/routes/               # FastAPI routers
│   └── wallet.py             # Wallet endpoints
└── database/
    ├── engine.py             # SQLModel engine with connection pooling
    └── seeders.py            # Database seeding utilities
```

### Key Architectural Patterns

1. **Session Management**: Each service method creates its own SQLModel `Session` context. Sessions are NOT shared across operations—wallet operations open and close their own session within each method.

2. **Repository Pattern**: Repositories handle database CRUD operations. Services call repositories and contain business logic. Controllers (routes) are thin adapters between HTTP and services.

3. **FX Rate Service**: Singleton service (`fx_rate_service`) manages exchange rates with three modes:
   - `static`: Fixed rates from config
   - `random`: Randomly selects from configured values on schedule
   - `api`: Fetches from exchangerate-api.com on schedule

   The scheduler starts during FastAPI's lifespan startup and stops on shutdown (see `src/main.py:13-24`).

4. **Transaction Model Design**: The `Transaction` model supports three operation types (`FUND`, `CONVERT`, `WITHDRAW`) with conditional fields:
   - Fund/Withdraw: use `currency` and `amount`
   - Convert: use `from_currency`, `to_currency`, `from_amount`, `to_amount`, `fx_rate`

5. **Decimal Precision**: All financial amounts use Python's `Decimal` type mapped to PostgreSQL `NUMERIC(20,2)` for amounts and `NUMERIC(20,4)` for exchange rates.

## Configuration System

Configuration is managed via `src/config/config.py` using pydantic-settings:

- Environment variables loaded from `.env` (see `.env.example` for template)
- Required: `DATABASE_URL`
- FX Rate Configuration:
  - `FX_RATE_MODE`: "static", "random", or "api"
  - `FX_RATE_UPDATE_INTERVAL`: seconds between updates (default 300)
  - `FX_RATE_RANDOM_VALUES`: comma-separated list for random mode
  - `EXCHANGERATE_API_URL`: API endpoint for external rates

The `Settings` class is instantiated as a singleton `settings` object imported throughout the application.

## Database Patterns

### Wallet Uniqueness

Wallets have a unique constraint on `(user_id, currency)`. The repository's `get_or_create` method leverages this:

```python
# In WalletRepository.get_or_create (src/repositories/wallet_repository.py)
# Attempts to get existing wallet, creates if not found
```

### Transaction Tracking

All wallet operations create a corresponding transaction record. This provides a complete audit trail. When performing a currency conversion, the service:

1. Validates balances
2. Updates both wallets (debit source, credit destination)
3. Creates a single CONVERT transaction with all details

### Migration Management

Alembic is configured with:
- Migration scripts in `alembic/versions/`
- `alembic/env.py` imports all models for autogeneration
- Run `make db-migrate` to apply migrations

When creating new models or modifying existing ones, generate a new migration:
```bash
uv run alembic revision --autogenerate -m "description"
```

## Logging Conventions

The application uses structlog for structured JSON logging. Logger setup is in `src/config/logging_config.py`.

**Pattern**: Use semantic event names with structured context:

```python
logger.info(
    "wallet_funded",
    user_id=user_id,
    currency=currency.value,
    amount=str(amount),
    transaction_id=transaction.id
)
```

**Important**: Convert `Decimal` types to strings for logging to ensure proper JSON serialization.

## API Endpoint Structure

All wallet endpoints are under `/wallets/{user_id}/`:
- `POST /wallets/{user_id}/fund` - Add funds
- `POST /wallets/{user_id}/convert` - Convert between currencies
- `POST /wallets/{user_id}/withdraw` - Withdraw funds
- `GET /wallets/{user_id}/balances` - Get all balances
- `GET /wallets/{user_id}/transactions?limit=100` - Get transaction history

Additionally:
- `GET /fx-rates` - Get current exchange rates

The wallet router is included in `main.py` and all routes are documented with OpenAPI responses.

## Testing Approach

Tests are run with pytest:
```bash
make test  # or: uv run pytest
```

Currently no tests exist, but when adding tests:
- Use pytest fixtures for database sessions
- Use pytest-asyncio for async endpoint tests
- Consider using a separate test database

## Docker Deployment

The Docker setup uses:
- Multi-stage build with `uv` for dependency management
- PostgreSQL 15 Alpine container with health checks
- Volume mounting for hot-reload development
- Container service dependencies (API waits for healthy Postgres)

The API container runs uvicorn on port 80 internally, exposed as 3700 on the host.

## Common Gotchas

1. **User ID Type Mismatch**: Routes use `str` for `user_id` but the database models use `int`. Services expect strings and convert as needed. This is intentional to support future string-based user IDs.

2. **FX Rate Scheduler**: The scheduler only starts if `FX_RATE_MODE` is "random" or "api". In "static" mode, the scheduler is not initialized.

3. **Session Contexts**: Don't try to access model attributes outside the session context where they were loaded. If needed, refresh objects or pass primitive values.

4. **Decimal JSON Encoding**: Models define `json_encoders` in their Config to convert `Decimal` to `str` for JSON responses.

5. **Database URL**: For local development, use `postgresql://postgres:postgres@localhost:5432/fx_payment_processor`. Docker uses `@postgres:5432` (container networking).
