# LTS-US-API-Python

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)

Enterprise-grade User Management and Project Tracking API for Lucas Technology Services. Built with FastAPI, PostgreSQL, and modern Python tooling.

## ✨ Features

- **🔐 JWT-based Authentication** - Secure token-based authentication system
- **🏢 Organization Management** - Multi-tenant organization support
- **👥 User Management** - Role-based user access control
- **📊 Project Management** - Full Agile project lifecycle management
- **📋 Work Item Tracking** - Epics, Features, User Stories, Tasks, Bugs
- **🏃 Sprint Management** - Scrum sprint planning and tracking
- **🖼️ Image Processing** - Advanced image upload, optimization, and duplicate detection
- **🔐 Credential Management** - Secure credential storage and management
- **🌐 CORS Support** - Pre-configured for frontend integration
- **📝 Comprehensive Logging** - Structured logging for debugging and monitoring

## 🛠️ Technology Stack

- **Python 3.12+** - Core programming language
- **FastAPI** - Modern, fast web framework
- **PostgreSQL 16+** - Primary database
- **SQLAlchemy 2.0** - ORM and database toolkit
- **Pydantic 2.5** - Data validation and settings management
- **JWT** - JSON Web Token authentication
- **Pillow** - Image processing
- **python-magic** - File type detection
- **bcrypt** - Password hashing
- **Uvicorn** - ASGI server

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- PostgreSQL 16 or higher
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Lucas-Technology-Services/LTS-US-API-Python.git
cd LTS-US-API-Python
```

2. **Create and activate virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. **Set up PostgreSQL database**
```sql
-- Create database and user
CREATE DATABASE lts_us_db;
CREATE USER lts_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE lts_us_db TO lts_user;
```

6. **Initialize database**
```bash
python -c "from app.database import init_db; init_db()"
```

7. **Run the API**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## 📁 Project Structure

```
LTS-US-API-Python/
├── app/
│   ├── __init__.py
│   ├── main.py              # Main FastAPI application
│   ├── database.py          # Database connection and models
│   ├── auth_service.py      # Authentication service
│   ├── image_service.py     # Image processing service
│   ├── organization_service.py
│   ├── project_service.py
│   ├── credential_service.py
│   ├── user_service.py
│   ├── crud.py             # CRUD operations
│   ├── schemas.py          # Pydantic schemas
│   └── models.py           # SQLAlchemy models
├── tests/                  # Test files
├── .env.example           # Environment variables template
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── LICENSE               # MIT License
```

## 🔌 API Endpoints

### Authentication (`/auth/*`)
- `POST /auth/token` - Generate JWT token
- `POST /auth/validate` - Validate JWT token
- `GET /auth/token/{client_id}` - Get valid token for client
- `DELETE /auth/cleanup` - Clean up expired tokens

### Organizations (`/organizations/*`)
- `POST /organizations` - Create new organization
- `GET /organizations` - List all organizations
- `GET /organizations/name/{name}` - Get organizations by name
- `GET /organizations/cnpj/{cnpj}` - Get organization by CNPJ
- `GET /organizations/ein/{ein}` - Get organization by EIN
- `POST /organizations/search` - Search organizations
- `POST /organizations/validate` - Validate organization data

### Users (`/users/*`)
- `POST /users/register` - Register new user
- `POST /users/login` - User login
- `GET /users/{user_id}` - Get user by ID
- `GET /users` - Get all users in organization
- `PUT /users/{user_id}` - Update user
- `POST /users/{user_id}/change-password` - Change password
- `DELETE /users/{user_id}` - Delete user
- `POST /users/reset-password` - Reset password

### Projects (`/projects/*`)
- `POST /projects` - Create project
- `GET /projects/{project_code}` - Get project by code
- `GET /projects` - Get organization projects
- `PUT /projects/{project_code}` - Update project
- `DELETE /projects/{project_code}` - Delete project
- `POST /projects/{project_code}/restore` - Restore project
- `POST /projects/validate-code` - Validate project code
- `POST /projects/search` - Search projects
- `GET /projects/{project_code}/stats` - Get project statistics
- `GET /projects-raw` - Get raw projects list

### Project Members (`/projects/{project_code}/members/*`)
- `POST /projects/{project_code}/members` - Add member
- `GET /projects/{project_code}/members` - List members
- `PUT /projects/{project_code}/members/{username}` - Update member role
- `DELETE /projects/{project_code}/members/{username}` - Remove member

### Work Items (`/projects/{project_code}/work-items/*`)
- `POST /projects/{project_code}/work-items` - Create work item
- `GET /projects/{project_code}/work-items/{work_item_id}` - Get work item

### Sprints (`/projects/{project_code}/sprints/*`)
- `POST /projects/{project_code}/sprints` - Create sprint

### Credentials (`/credentials/*`)
- `POST /credentials` - Create credential
- `GET /credentials` - List credentials
- `GET /credentials/{credential_id}` - Get credential by ID
- `PUT /credentials/{credential_id}` - Update credential
- `DELETE /credentials/{credential_id}` - Delete credential
- `POST /credentials/search` - Search credentials
- `POST /credentials/validate-email` - Validate email
- `GET /credentials/stats` - Get credential statistics
- `GET /credentials/by-type/{type}` - Get credentials by type

### Images (`/organizations/{organization_name}/posts/{post_id}/image/*`)
- `POST /upload-file` - Upload image from file
- `POST /upload-base64` - Upload image from base64
- `GET /` - Get post image
- `GET /raw` - Get raw image
- `DELETE /` - Delete image
- `GET /stats` - Get image statistics
- `GET /by-image-status` - Get posts by image status
- `POST /bulk/update-metadata` - Bulk update metadata
- `POST /cleanup` - Cleanup orphaned images

### Image Processing (`/images/*`)
- `POST /validate` - Validate image
- `POST /optimize` - Optimize image
- `POST /batch/optimize` - Batch optimize images

### Monitoring
- `POST /health` - Health check
- `POST /` - Root endpoint
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://lts_user:password@localhost:5432/lts_us_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=lts_us_db
DB_USER=lts_user
DB_PASSWORD=your_secure_password

# JWT Configuration
JWT_SECRET=your_super_secret_jwt_key_change_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440  # 24 hours

# CORS
CORS_ORIGINS=["https://lts-us-website.vercel.app"]
```

### Database Models

The application includes the following main models:
- `Organization` - Companies/entities
- `User` - System users with roles
- `Project` - Agile projects
- `WorkItem` - Tasks, stories, bugs
- `Sprint` - Development sprints
- `Credential` - Login credentials
- `PostImage` - Image attachments

## 🧪 Testing

Run tests with pytest:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py -v
```

## 📊 Database Schema

![Database Schema](docs/database_schema.png)

Key relationships:
- Organizations have many Users
- Organizations have many Projects
- Projects have many WorkItems and Sprints
- Users can be members of multiple Projects
- Posts can have one Image

## 🚢 Deployment

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://lts_user:password@db:5432/lts_us_db
    depends_on:
      - db
    volumes:
      - ./app:/app/app

  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=lts_us_db
      - POSTGRES_USER=lts_user
      - POSTGRES_PASSWORD=your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### Production Considerations

1. **Use environment variables** for secrets
2. **Enable HTTPS** with SSL certificates
3. **Configure proper CORS** for your frontend
4. **Set up database backups**
5. **Implement rate limiting**
6. **Monitor with logging and metrics**
7. **Use a process manager** (Supervisor, systemd)

## 📈 Performance

- **FastAPI async/await** for high concurrency
- **Database connection pooling**
- **Image optimization** on upload
- **Duplicate detection** to save storage
- **Pagination** on list endpoints
- **Caching** for frequently accessed data

## 🔒 Security

- **JWT authentication** with expiration
- **Password hashing** using bcrypt
- **SQL injection prevention** via SQLAlchemy
- **Input validation** with Pydantic
- **CORS configuration** for specific origins
- **File type validation** for uploads
- **Secure headers** middleware

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write type hints for all functions
- Add tests for new features
- Update documentation
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, email [support@lucastechnologyservices.com](mailto:support@lucastechnologyservices.com) or open an issue in the GitHub repository.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [PostgreSQL](https://www.postgresql.org/) for the reliable database
- [SQLAlchemy](https://www.sqlalchemy.org/) for the ORM
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation

---

### Demmands and Goals:

<!-- Generated by sourcery-ai[bot]: start review_guide -->

## Reviewer's Guide

Implements a full accounting costs and FX subsystem: new exchange rate and cost domain services with Postgres access, AwesomeAPI-based FX sync service with scheduler, related FastAPI models and endpoints, plus wiring into app startup/shutdown and some refactors to image service DB access.

#### Sequence diagram for AwesomeAPI organization sync endpoint

```mermaid
sequenceDiagram
    actor Client
    participant FastAPIApp as FastAPI_app
    participant AuthTokenService as auth_token_service
    participant AwesomeService as awesomeapi_sync_service
    participant AwesomeAPI as awesomeapi_http_api
    participant DB as postgres_db

    Client->>FastAPIApp: POST /awesome-api/sync/organization
    FastAPIApp->>AuthTokenService: validate_token(token)
    AuthTokenService-->>FastAPIApp: token_valid
    FastAPIApp->>AwesomeService: sync_for_organization(organization_id)
    activate AwesomeService
    AwesomeService->>AwesomeAPI: GET /last/USD-BRL
    AwesomeAPI-->>AwesomeService: rate_json
    AwesomeService->>DB: INSERT/UPDATE accounting.exchange_rates
    DB-->>AwesomeService: write_result
    AwesomeService-->>FastAPIApp: AwesomeAPISyncResponse
    deactivate AwesomeService
    FastAPIApp-->>Client: 200 OK AwesomeAPISyncResponse
```

#### Sequence diagram for creating a cost with automatic FX lookup

```mermaid
sequenceDiagram
    actor Client
    participant FastAPIApp as FastAPI_app
    participant AuthTokenService as auth_token_service
    participant CostService as cost_service
    participant ExchangeRateService as exchange_rate_service
    participant DB as postgres_db

    Client->>FastAPIApp: POST /costs (CostCreateRequest)
    FastAPIApp->>AuthTokenService: validate_token(token)
    AuthTokenService-->>FastAPIApp: token_valid
    FastAPIApp->>CostService: create_cost(due_date, amount, currency, organization_id, ...)
    activate CostService
    alt non_BRL_and_missing_rate
        CostService->>ExchangeRateService: get_exchange_rate_for_period(organization_id, year_month, base_currency, target_currency)
        ExchangeRateService->>DB: SELECT FROM accounting.exchange_rates
        DB-->>ExchangeRateService: rate_row_or_none
        ExchangeRateService-->>CostService: exchange_rate_or_none
        alt rate_not_found_for_period
            CostService->>ExchangeRateService: get_exchange_rate_for_date(organization_id, due_date, base_currency, target_currency)
            ExchangeRateService->>DB: SELECT FROM accounting.exchange_rates
            DB-->>ExchangeRateService: rate_row_or_none
            ExchangeRateService-->>CostService: exchange_rate_or_none
        end
        CostService->>CostService: compute converted_amount_brl
    else currency_BRL
        CostService->>CostService: set converted_amount_brl = amount
    end
    CostService->>DB: INSERT INTO accounting.costs
    DB-->>CostService: created_cost_row
    CostService-->>FastAPIApp: created_cost_dict
    deactivate CostService
    FastAPIApp-->>Client: 200 OK CostResponse
```

#### Sequence diagram for daily scheduled FX sync

```mermaid
sequenceDiagram
    participant Startup as FastAPI_startup_event
    participant AwesomeService as awesomeapi_sync_service
    participant Scheduler as scheduler_loop
    participant AwesomeAPI as awesomeapi_http_api
    participant DB as postgres_db

    Startup->>AwesomeService: start_scheduler()
    AwesomeService->>Scheduler: create_task(_scheduler_loop)
    loop daily
        Scheduler->>Scheduler: calculate_next_run()
        Scheduler->>Scheduler: sleep_until_next_run
        Scheduler->>AwesomeService: sync_all_organizations()
        AwesomeService->>AwesomeAPI: GET /last/USD-BRL
        AwesomeAPI-->>AwesomeService: rate_json
        AwesomeService->>DB: upsert accounting.exchange_rates for all organizations
        DB-->>AwesomeService: write_results
    end
```

#### ER diagram for new accounting.costs and accounting.exchange_rates tables

```mermaid
erDiagram
    organizations {
        UUID id PK
        text name
        timestamp created_at
        timestamp deleted_at
    }

    accounting_exchange_rates {
        UUID id PK
        varchar year_month
        varchar base_currency
        varchar target_currency
        decimal rate
        varchar source
        date valid_from
        date valid_to
        UUID organization_id FK
        timestamp created_at
        timestamp updated_at
    }

    accounting_costs {
        UUID id PK
        date due_date
        decimal amount
        varchar currency
        varchar payment_nature
        varchar cost_nature_code
        UUID organization_id FK
        decimal converted_amount_brl
        varchar exchange_rate_month
        decimal exchange_rate_value
        text description
        varchar status
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    organizations ||--o{ accounting_exchange_rates : has_rates
    organizations ||--o{ accounting_costs : has_costs
```

#### ER diagram focusing on organization-wide FX reuse for costs

```mermaid
erDiagram
    organizations {
        UUID id PK
        text name
    }

    accounting_exchange_rates {
        UUID id PK
        UUID organization_id FK
        varchar year_month
        varchar base_currency
        varchar target_currency
        decimal rate
    }

    accounting_costs {
        UUID id PK
        UUID organization_id FK
        date due_date
        decimal amount
        varchar currency
        varchar exchange_rate_month
        decimal exchange_rate_value
        decimal converted_amount_brl
    }

    organizations ||--o{ accounting_exchange_rates : owns_rates
    organizations ||--o{ accounting_costs : owns_costs

    accounting_exchange_rates ||--o{ accounting_costs : matched_by_month
```

#### Class diagram for core accounting and FX services

```mermaid
classDiagram
    class AwesomeAPISyncService {
        - BASE_API_URL: str
        - DEFAULT_PAIR: str
        - sync_hour: int
        - sync_minute: int
        - sync_task: asyncio_Task
        - is_running: bool
        - scheduler_task: asyncio_Task
        - rate_cache: Dict
        - cache_expiry: timedelta
        + __init__(sync_hour: int, sync_minute: int)
        + sync_for_organization(organization_id: UUID) Dict
        + sync_all_organizations() Dict
        + start_scheduler()
        + stop_scheduler()
        + manual_sync_now() Dict
        + get_sync_status() Dict
        + get_current_rate(use_cache: bool) Dict
        + get_organization_rates(organization_id: UUID, months_back: int) List
        - _fetch_live_rate_from_api() Dict
        - _store_exchange_rate(organization_id: UUID, rate_data: Dict, force_update: bool) bool
        - _get_all_active_organizations() List
        - _calculate_next_run() datetime
        - _scheduler_loop()
        - _execute_sql(query: str, params: tuple) bool
        - _fetch_one_sql(query: str, params: tuple) Dict
        - _fetch_all_sql(query: str, params: tuple) List
    }

    class ExchangeRateService {
        + __init__()
        + create_exchange_rate(year_month: str, rate: Decimal, valid_from: date, valid_to: date, organization_id: UUID, base_currency: str, target_currency: str, source: str) Dict
        + get_exchange_rate_by_id(rate_id: UUID) Dict
        + update_exchange_rate(rate_id: UUID, year_month: str, rate: Decimal, valid_from: date, valid_to: date, base_currency: str, target_currency: str, source: str) Dict
        + delete_exchange_rate(rate_id: UUID) bool
        + get_organization_exchange_rates(organization_id: UUID, year_month: str, base_currency: str, target_currency: str, date_from: date, date_to: date, page: int, page_size: int) Dict
        + get_exchange_rate_for_period(organization_id: UUID, year_month: str, base_currency: str, target_currency: str) Dict
        + get_exchange_rate_for_date(organization_id: UUID, target_date: date, base_currency: str, target_currency: str) Dict
        + get_latest_exchange_rate(organization_id: UUID, base_currency: str, target_currency: str) Dict
        + get_available_periods(organization_id: UUID, base_currency: str, target_currency: str) List
        + get_available_currency_pairs(organization_id: UUID, year_month: str) List
        + batch_create_exchange_rates(rates_data: List, organization_id: UUID) Dict
        + get_organization_summary(organization_id: UUID) Dict
    }

    class CostService {
        - exchange_rate_service: ExchangeRateService
        + __init__(exchange_rate_service: ExchangeRateService)
        + create_cost(due_date: date, amount: Decimal, currency: str, payment_nature: str, cost_nature_code: str, organization_id: UUID, converted_amount_brl: Decimal, exchange_rate_month: str, exchange_rate_value: Decimal, description: str, status: str) Dict
        + get_cost_by_id(cost_id: UUID) Dict
        + update_cost(cost_id: UUID, due_date: date, amount: Decimal, currency: str, payment_nature: str, cost_nature_code: str, converted_amount_brl: Decimal, exchange_rate_month: str, exchange_rate_value: Decimal, description: str, status: str) Dict
        + delete_cost(cost_id: UUID) bool
        + get_organization_costs(organization_id: UUID, start_date: date, end_date: date, status: str, cost_nature_code: str, currency: str, page: int, page_size: int) Dict
        + update_cost_status(cost_id: UUID, status: str) bool
        + update_exchange_rate_data(cost_id: UUID, converted_amount_brl: Decimal, exchange_rate_month: str, exchange_rate_value: Decimal) bool
        + get_costs_by_exchange_rate_month(organization_id: UUID, exchange_rate_month: str) List
        + get_monthly_summary(organization_id: UUID, year: int, month: int) Dict
        + bulk_update_status(cost_ids: List~UUID~, status: str) int
        + restore_cost(cost_id: UUID) Dict
        + get_organization_summary(organization_id: UUID, start_date: date, end_date: date) Dict
        + get_costs_without_exchange_rate(organization_id: UUID) List
        + get_overdue_costs(organization_id: UUID, cutoff_date: date) List
        + auto_update_exchange_rates_for_costs(organization_id: UUID) Dict
    }

    class ImageService {
        + MAX_IMAGE_SIZE: int
        + ALLOWED_MIME_TYPES: set
        + __init__()
        - _execute_sql(query: str, params: tuple) bool
        - _fetch_one_sql(query: str, params: tuple) Dict
        - _fetch_all_sql(query: str, params: tuple) List
        + validate_and_process_image(base64_data: str, mime_type: str) Dict
        + save_image_to_post(post_id: UUID, image_data: Dict) bool
        + get_post_image(post_id: UUID, include_metadata: bool) Dict
        + remove_post_image(post_id: UUID) bool
        + find_duplicate_image(image_hash: str, exclude_post_id: UUID) List
        + get_posts_by_image_status(organization_id: UUID, has_image: bool) List
        + bulk_update_image_metadata(updates: List~Dict~) Dict
        + get_image_statistics(organization_id: UUID) Dict
        + cleanup_orphaned_images(organization_id: UUID, days_threshold: int) Dict
    }

    class Database {
        + get_async_connection()
    }

    Database <.. AwesomeAPISyncService : uses
    Database <.. ExchangeRateService : uses
    Database <.. CostService : uses
    Database <.. ImageService : uses

    ExchangeRateService <.. AwesomeAPISyncService : stores_rates
    ExchangeRateService <.. CostService : lookup_rates

    AwesomeAPISyncService <.. FastAPIApp : global_instance
    ExchangeRateService <.. FastAPIApp : global_instance
    CostService <.. FastAPIApp : global_instance
    ImageService <.. FastAPIApp : global_instance
```

#### Class diagram for new accounting and AwesomeAPI Pydantic models

```mermaid
classDiagram
    class ExchangeRateCreateRequest {
        token: str
        organization_id: UUID
        year_month: str
        rate: float
        valid_from: date
        valid_to: date
        base_currency: str
        target_currency: str
        source: str
    }

    class ExchangeRateUpdateRequest {
        token: str
        year_month: str
        rate: float
        valid_from: date
        valid_to: date
        base_currency: str
        target_currency: str
        source: str
    }

    class ExchangeRateResponseModel {
        id: UUID
        year_month: str
        base_currency: str
        target_currency: str
        rate: float
        source: str
        valid_from: date
        valid_to: date
        organization_id: UUID
        created_at: datetime
        updated_at: datetime
    }

    class ExchangeRateListResponse {
        exchange_rates: List~ExchangeRateResponseModel~
        total_count: int
        page: int
        page_size: int
        total_pages: int
    }

    class ExchangeRatePeriodRequest {
        token: str
        organization_id: UUID
        year_month: str
        base_currency: str
        target_currency: str
    }

    class ExchangeRateDateRequest {
        token: str
        organization_id: UUID
        target_date: date
        base_currency: str
        target_currency: str
    }

    class ExchangeRateBatchCreateRequest {
        token: str
        organization_id: UUID
        rates_data: List~Dict~
    }

    class ExchangeRateBatchCreateResponse {
        created_count: int
        failed_count: int
        errors: List~str~
    }

    class ExchangeRateSummaryResponse {
        statistics: Dict
        currency_pairs: List~Dict~
    }

    class CostCreateRequest {
        token: str
        organization_id: UUID
        due_date: date
        amount: float
        currency: str
        payment_nature: str
        cost_nature_code: str
        converted_amount_brl: float
        exchange_rate_month: str
        exchange_rate_value: float
        description: str
        status: str
    }

    class CostUpdateRequest {
        token: str
        due_date: date
        amount: float
        currency: str
        payment_nature: str
        cost_nature_code: str
        converted_amount_brl: float
        exchange_rate_month: str
        exchange_rate_value: float
        description: str
        status: str
    }

    class CostResponse {
        id: UUID
        due_date: date
        amount: float
        currency: str
        payment_nature: str
        cost_nature_code: str
        organization_id: UUID
        converted_amount_brl: float
        exchange_rate_month: str
        exchange_rate_value: float
        description: str
        status: str
        created_at: datetime
        updated_at: datetime
        deleted_at: datetime
    }

    class CostListResponse {
        costs: List~CostResponse~
        total_count: int
        page: int
        page_size: int
        total_pages: int
    }

    class CostSummaryResponse {
        total_costs: int
        total_amount: float
        pending_amount: float
        paid_amount: float
        overdue_amount: float
        pending_count: int
        paid_count: int
        overdue_count: int
        distinct_currencies: int
        distinct_natures: int
        total_converted_brl: float
    }

    class CostMonthlySummaryResponse {
        total_costs: int
        total_amount: float
        average_amount: float
        min_amount: float
        max_amount: float
        distinct_currencies: int
        distinct_natures: int
        paid_count: int
        pending_count: int
        overdue_count: int
    }

    class CostStatusUpdateRequest {
        token: str
        organization_id: UUID
        status: str
    }

    class CostBulkStatusUpdateRequest {
        token: str
        organization_id: UUID
        cost_ids: List~UUID~
        status: str
    }

    class CostExchangeRateUpdateRequest {
        token: str
        organization_id: UUID
        converted_amount_brl: float
        exchange_rate_month: str
        exchange_rate_value: float
    }

    class CostAutoUpdateExchangeRatesResponse {
        success: bool
        updated_count: int
        failed_count: int
        total_processed: int
        errors: List~str~
    }

    class CostFilterRequest {
        token: str
        organization_id: UUID
        start_date: date
        end_date: date
        status: str
        cost_nature_code: str
        currency: str
        page: int
        page_size: int
    }

    class AwesomeAPISyncRequest {
        token: str
        organization_id: UUID
    }

    class AwesomeAPISyncResponse {
        success: bool
        organization_id: str
        rate: float
        bid: float
        ask: float
        timestamp: str
        duration_seconds: float
        source: str
        error: str
    }

    class AwesomeAPISyncAllResponse {
        success: bool
        synced_count: int
        failed_count: int
        total_organizations: int
        rate: float
        results: List~Dict~
        timestamp: str
        duration_seconds: float
        error: str
    }

    class AwesomeAPISyncStatusResponse {
        is_running: bool
        sync_hour: int
        sync_minute: int
        next_run: str
        cache_size: int
    }

    class AwesomeAPIManualSyncResponse {
        success: bool
        message: str
        data: Dict
    }

    ExchangeRateResponseModel <.. ExchangeRateListResponse : element
    CostResponse <.. CostListResponse : element

    AwesomeAPISyncRequest <.. AwesomeAPISyncResponse : request_response
    AwesomeAPISyncRequest <.. AwesomeAPISyncAllResponse : request_response

    CostCreateRequest <.. CostResponse : creates
    CostUpdateRequest <.. CostResponse : updates

    ExchangeRateCreateRequest <.. ExchangeRateResponseModel : creates
    ExchangeRateUpdateRequest <.. ExchangeRateResponseModel : updates
```

### File-Level Changes

| Change | Details | Files |
| ------ | ------- | ----- |
| Add exchange rate domain model and service backed by accounting.exchange_rates table, including CRUD, queries, batch operations, and summary reporting. | <ul><li>Create ExchangeRateService with methods for CRUD, querying by period/date/latest, pagination, batch create, and organization-level statistics.</li><li>Implement direct async DB access for exchange rates using db.get_async_connection and psycopg-style cursors.</li><li>Define SQL DDL for accounting.exchange_rates table with constraints and indexes.</li></ul> | `app/exchange_rate_service.py`<br/>`queries/exchange_rates_tbl.sql` |
| Introduce cost domain model and service for accounting.costs with exchange-rate-aware creation, updates, and summaries. | <ul><li>Create CostService with methods to create/update/delete costs, filter by organization/date/status, bulk update status, restore soft-deleted costs, and compute various summaries.</li><li>Integrate cost creation/update flows with ExchangeRateService to auto-fill BRL conversions and exchange-rate metadata when needed.</li><li>Define SQL DDL for accounting.costs table with indexes for common query predicates.</li></ul> | `app/cost_service.py`<br/>`queries/costs_tbl.sql` |
| Integrate AwesomeAPI to fetch USD/BRL FX rates, persist them per organization, and schedule daily synchronization. | <ul><li>Implement AwesomeAPISyncService that calls AwesomeAPI, caches recent rates, writes into accounting.exchange_rates, and syncs all organizations.</li><li>Add async scheduler loop with configurable daily trigger time, manual sync, and status endpoints.</li><li>Expose global awesomeapi_sync_service instance and start/stop it on FastAPI app startup/shutdown.</li></ul> | `app/awesome_api_sync_service.py`<br/>`app/__init__.py`<br/>`app/main.py` |
| Expose new exchange-rate, cost, and AwesomeAPI endpoints in the FastAPI app using new Pydantic models. | <ul><li>Define request/response models for exchange rates, costs, and AwesomeAPI sync/status in main.py and supplemental schema types in app/schemas.py.</li><li>Add endpoints for creating and listing exchange rates, retrieving rates by period, creating and listing costs with filtering, and various AwesomeAPI-backed FX endpoints (per-organization sync, historical rates, current rate).</li><li>Hook endpoints into ExchangeRateService, CostService, and AwesomeAPISyncService and reuse existing token validation for auth.</li></ul> | `app/main.py`<br/>`app/schemas.py` |
| Refactor ImageService to use direct async SQL helpers instead of injected DB instance, aligning it with the new db access pattern. | <ul><li>Remove db_instance from ImageService constructor and use module-level db via new _execute_sql/_fetch_one_sql/_fetch_all_sql helpers.</li><li>Update image CRUD and statistics methods to call the new helpers instead of self.db.execute_query/fetch_one/execute_update.</li><li>Leave a global-friendly ImageService definition prepared for instantiation (though the instance wiring is not shown in this diff).</li></ul> | `app/image_service.py` |
| Wire new services into the app package and adjust minor infrastructure files. | <ul><li>Export awesomeapi_sync_service, exchange_rate_service, and cost_service from app.__init__ for easy import in main.py and other modules.</li><li>Slightly adjust auth/token validation helper and add app lifecycle logging around the FX scheduler.</li><li>Keep requirements.txt functionally unchanged and ensure gitignore/config are aligned with the new modules.</li></ul> | `app/__init__.py`<br/>`app/main.py`<br/>`requirements.txt`<br/>`.gitignore` |

### Possibly linked issues

- **#7**: They address the same expense registration API, including DB table, CostService, and endpoints; PR adds exchange-rate integration.

---

<details>
<summary>Tips and commands</summary>

#### Interacting with Sourcery

- **Trigger a new review:** Comment `@sourcery-ai review` on the pull request.
- **Continue discussions:** Reply directly to Sourcery's review comments.
- **Generate a GitHub issue from a review comment:** Ask Sourcery to create an
  issue from a review comment by replying to it. You can also reply to a
  review comment with `@sourcery-ai issue` to create an issue from it.
- **Generate a pull request title:** Write `@sourcery-ai` anywhere in the pull
  request title to generate a title at any time. You can also comment
  `@sourcery-ai title` on the pull request to (re-)generate the title at any time.
- **Generate a pull request summary:** Write `@sourcery-ai summary` anywhere in
  the pull request body to generate a PR summary at any time exactly where you
  want it. You can also comment `@sourcery-ai summary` on the pull request to
  (re-)generate the summary at any time.
- **Generate reviewer's guide:** Comment `@sourcery-ai guide` on the pull
  request to (re-)generate the reviewer's guide at any time.
- **Resolve all Sourcery comments:** Comment `@sourcery-ai resolve` on the
  pull request to resolve all Sourcery comments. Useful if you've already
  addressed all the comments and don't want to see them anymore.
- **Dismiss all Sourcery reviews:** Comment `@sourcery-ai dismiss` on the pull
  request to dismiss all existing Sourcery reviews. Especially useful if you
  want to start fresh with a new review - don't forget to comment
  `@sourcery-ai review` to trigger a new review!

#### Customizing Your Experience

Access your [dashboard](https://app.sourcery.ai) to:
- Enable or disable review features such as the Sourcery-generated pull request
  summary, the reviewer's guide, and others.
- Change the review language.
- Add, remove or edit custom review instructions.
- Adjust other review settings.

#### Getting Help

- [Contact our support team](mailto:support@sourcery.ai) for questions or feedback.
- Visit our [documentation](https://docs.sourcery.ai) for detailed guides and information.
- Keep in touch with the Sourcery team by following us on [X/Twitter](https://x.com/SourceryAI), [LinkedIn](https://www.linkedin.com/company/sourcery-ai/) or [GitHub](https://github.com/sourcery-ai).

</details>

<!-- Generated by sourcery-ai[bot]: end review_guide -->
