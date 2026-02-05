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

