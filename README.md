# FX Payment Processor

A multi-currency wallet system API built with FastAPI that supports USD and MXN currencies with real-time exchange rate updates.

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLModel
- **Migrations**: Alembic
- **Validation**: Pydantic
- **Logging**: structlog
- **Scheduler**: APScheduler
- **Package Manager**: uv
- **Containerization**: Docker & Docker Compose

## Architecture

### Overview

The application follows a layered architecture pattern with clear separation of concerns:

```
┌───────────────────────────────────────────────────────┐
│                      API Layer (Routes)               │
│              FastAPI endpoints for HTTP requests      │
└──────────────────────┬────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────┐
│                   Service Layer                       │
│  - Business logic and orchestration                   │
│  - WalletService: Wallet operations                   │
│  - FXRateService: Exchange rate management            │
└──────────────────────┬────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────┐
│                Repository Layer                       │
│  - Data access abstraction                            │
│  - WalletRepository: Wallet CRUD operations           │
│  - TransactionRepository: Transaction queries         │
└──────────────────────┬────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────┐
│                    Database Layer                     │
│  - PostgreSQL with SQLModel                           │
│  - Wallet: User currency balances                     │
│  - Transaction: Transaction history                   │
└───────────────────────────────────────────────────────┘
```

### Components

#### 1. **API Layer** (`src/api/routes/`)
- **wallet.py**: RESTful endpoints for wallet operations
- Handles HTTP requests/responses
- Input validation via Pydantic schemas
- Error handling and status codes

#### 2. **Service Layer** (`src/services/`)
- **wallet_service.py**: Core business logic for wallet operations
  - Fund wallet
  - Currency conversion
  - Withdraw funds
  - Balance queries
  - Transaction history
- **fx_rates.py**: Exchange rate management
  - Static, random, or API-based rate updates
  - Background scheduler for periodic updates
  - Supports USD ↔ MXN conversions

#### 3. **Repository Layer** (`src/repositories/`)
- **wallet_repository.py**: Database operations for wallets
  - Get/create wallets by user and currency
  - Update wallet balances
  - Query all wallets for a user
- **transaction_repository.py**: Transaction data access
  - Create transactions
  - Query transactions by user

#### 4. **Models** (`src/models/`)
- **wallet.py**: Wallet entity (user_id, currency, balance)
- **transaction.py**: Transaction entity with support for fund/convert/withdraw types
- **currency.py**: Currency enum (USD, MXN)
- **user.py**: User model

#### 5. **Schemas** (`src/schemas/`)
- Pydantic models for request/response validation
- Request models: `FundRequest`, `ConvertRequest`, `WithdrawRequest`
- Response models: `FundResponse`, `ConvertResponse`, `WithdrawResponse`, `BalancesResponse`, `TransactionListResponse`

#### 6. **Configuration** (`src/config/`)
- **config.py**: Application settings (database, FX rates, etc.)
- **logging_config.py**: Structured logging setup with structlog

#### 7. **Database** (`src/database/`)
- **engine.py**: SQLModel database engine and session management
- Alembic migrations for schema versioning

### FX Rate Service

The FX Rate Service supports three modes:

1. **Static Mode**: Fixed exchange rates (default)
2. **Random Mode**: Randomly selects from a predefined list of rates at intervals
3. **API Mode**: Fetches real-time rates from an external API (ExchangeRate-API)

The service uses APScheduler to update rates periodically when not in static mode.

## API Interfaces

### Base URL
- Local: `http://localhost:3700`
- Docker: `http://localhost:3700`

### Endpoints

#### Fund Wallet
**POST** `/wallets/{user_id}/fund`

Add funds to a user's wallet in the specified currency.

**Request Body:**
```json
{
  "currency": "USD",
  "amount": "100.00"
}
```

**Response (201):**
```json
{
  "user_id": "user123",
  "currency": "USD",
  "amount": "100.00",
  "new_balance": "100.00",
  "message": "Wallet funded successfully"
}
```

#### Convert Currency
**POST** `/wallets/{user_id}/convert`

Convert funds between USD and MXN using current exchange rates.

**Request Body:**
```json
{
  "from_currency": "USD",
  "to_currency": "MXN",
  "amount": "100.00"
}
```

**Response (200):**
```json
{
  "user_id": "user123",
  "from_currency": "USD",
  "to_currency": "MXN",
  "from_amount": "100.00",
  "to_amount": "1870.00",
  "fx_rate": "18.70",
  "message": "Currency converted successfully"
}
```

#### Withdraw Funds
**POST** `/wallets/{user_id}/withdraw`

Withdraw funds from a user's wallet.

**Request Body:**
```json
{
  "currency": "USD",
  "amount": "50.00"
}
```

**Response (200):**
```json
{
  "user_id": "user123",
  "currency": "USD",
  "amount": "50.00",
  "new_balance": "50.00",
  "message": "Funds withdrawn successfully"
}
```

#### Get Balances
**GET** `/wallets/{user_id}/balances`

Retrieve all wallet balances for a user across all currencies.

**Response (200):**
```json
{
  "balances": {
    "USD": "500.00",
    "MXN": "9350.00"
  }
}
```

#### Get FX Rates
**GET** `/fx-rates`

Get current exchange rates.

**Response (200):**
```json
{
  "usd_to_mxn": 18.70,
  "mxn_to_usd": 0.053,
  "mode": "random"
}
```

### API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:3700/docs`
- ReDoc: `http://localhost:3700/redoc`

## Commands to Run the Application

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker and Docker Compose (for containerized deployment)

### Simple setup (Recommended)

Install dependencies:
This commands:
1. Builds Docker containers
2. Starts all services (API + PostgreSQL)
3. Reset and runs database migrations
4. Seeds the database with test data
```bash
make install
make run
# or
uv sync
```

### Local Development

#### Start Database (Docker)
```bash
docker-compose up -d postgres
```

#### Run Migrations
```bash
make db-migrate
# or
uv run alembic upgrade head
```

#### Seed Database (Optional)
```bash
make db-seed
# or
uv run python scripts/seed_db.py
```

#### Run Development Server
```bash
make dev
# or
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 3700
```

The API will be available at `http://localhost:3700`

#### Manual Docker Commands

Build containers:
```bash
make docker-build
# or
docker-compose build
```

Start services:
```bash
make docker-up
# or
docker-compose up -d
```

Stop services:
```bash
make docker-down
# or
docker-compose down
```

View logs:
```bash
make docker-logs
# or
docker-compose logs -f
```
### Testing

Run tests:
```bash
make test
# or
uv run pytest
```

### Project Structure

```
fx_payment_processor/
├── alembic/              # Database migrations
├── scripts/              # Utility scripts (seed_db.py)
├── src/
│   ├── api/              # API routes
│   │   └── routes/
│   │       └── wallet.py
│   ├── config/           # Configuration
│   ├── database/         # Database setup
│   ├── models/           # SQLModel entities
│   ├── repositories/     # Data access layer
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── main.py           # FastAPI application
├── docker-compose.yml    # Docker services
├── Dockerfile            # Container definition
├── Makefile              # Build automation
└── pyproject.toml        # Project dependencies
```


