# Apartment Management System

A full-featured property management platform built with Django and Django REST Framework to simplify property, payment, and communication management. It was designed to provide secure authentication and role-based access control for landlords, caretakers, and tenants, improving transparency and efficiency in property operations.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Security Features](#security-features)
- [User Roles](#user-roles)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

### Core Functionality
- **Role-Based Access Control**: 3-tier user system (Landlord, Caretaker, Tenant)
- **Property Management**: Complete CRUD for properties and units
- **Payment Tracking**: Integration-ready payment system with multiple payment methods
- **Communication System**: Smart notice targeting with read receipts
- **Secure Authentication**: JWT tokens stored in httpOnly cookies (XSS protection)

### Security Features
- ✅ HttpOnly cookie-based authentication
- ✅ CSRF protection with SameSite cookies
- ✅ Role-based permissions at object level
- ✅ Password validation and hashing
- ✅ Email uniqueness constraints
- ✅ Secure token refresh mechanism

### Business Logic
- ✅ Role-based user registration hierarchy
- ✅ Property-Unit-Tenant relationships
- ✅ Payment status tracking (pending/completed/failed)
- ✅ Audience targeting for notices
- ✅ Financial reporting and analytics
- ✅ Read status tracking for communications

## Tech Stack

**Backend:**
- Python 3.11+
- Django 5.2
- Django REST Framework
- PostgreSQL
- SimpleJWT (Custom cookie implementation)

**Key Libraries:**
- `djangorestframework` - API framework
- `djangorestframework-simplejwt` - JWT authentication
- `django-cors-headers` - CORS handling
- `psycopg2-binary` - PostgreSQL adapter
- `python-decouple` - Environment configuration

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Django Backend                       │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │ Accounts │  │Properties│  │ Payments │  │Notices ││
│  │  (Auth)  │  │ & Units  │  │  System  │  │ System ││
│  └──────────┘  └──────────┘  └──────────┘  └────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │        Role-Based Permissions Layer             │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │    JWT Cookie Authentication (httpOnly)         │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓
              ┌───────────────────────┐
              │   PostgreSQL Database │
              └───────────────────────┘
```

## Installation

### Prerequisites
- Python 3.11 or higher
- PostgreSQL 14 or higher
- pip (Python package manager)
- Virtual environment tool

### Step 1: Clone the Repository
```bash
git clone https://github.com/E-ugine/ApartmentHub.git
cd ApartmentHub
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Database Setup

**Create PostgreSQL Database:**
```sql
CREATE DATABASE apartment_mgmt_db;
CREATE USER apartment_user WITH PASSWORD 'your_secure_password';
ALTER ROLE apartment_user SET client_encoding TO 'utf8';
ALTER ROLE apartment_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE apartment_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE apartment_mgmt_db TO apartment_user;
```

### Step 5: Environment Configuration

Create a `.env` file in the project root: or `cp .env.example .env`

```env
SECRET_KEY=your-secret-key-here-generate-with-django
DEBUG=True
DB_NAME=apartment_mgmt_db
DB_USER=apartment_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

**Generate a secure SECRET_KEY:**
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### Step 6: Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 7: Create Superuser
```bash
python manage.py createsuperuser
```

### Step 8: Run Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/` to access the admin panel.

## Configuration

### Security Settings (Production)

Update `settings.py` for production:

```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Ensure HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# CORS for production
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
]
```

### JWT Token Configuration

Current settings (can be adjusted):
- Access Token Lifetime: 15 minutes
- Refresh Token Lifetime: 7 days
- Token Rotation: Enabled
- Cookie Security: httpOnly, Secure (in production), SameSite=Lax

## API Documentation

### Base URL
```
Development: http://127.0.0.1:8000/api/
Production: https://yourdomain.com/api/
```

### Authentication Endpoints

#### Login
```http
POST /api/accounts/auth/login/
Content-Type: application/json

{
    "username": "user@example.com",
    "password": "password123"
}

Response: 200 OK
{
    "user": {
        "id": 1,
        "username": "user",
        "email": "user@example.com",
        "role": "tenant",
        ...
    },
    "message": "Login successful"
}

Note: Tokens are set as httpOnly cookies automatically
```

#### Logout
```http
POST /api/accounts/auth/logout/
Authorization: Required (via cookies)

Response: 200 OK
{
    "message": "Logout successful"
}
```

#### Token Refresh
```http
POST /api/accounts/auth/token/refresh/
(Refresh token read from cookie automatically)

Response: 200 OK
{
    "message": "Token refreshed successfully"
}
```

#### User Registration (Role-based)
```http
POST /api/accounts/auth/register/
Authorization: Required (Landlord or Caretaker)
Content-Type: application/json

{
    "username": "newuser",
    "email": "new@example.com",
    "password": "securepass123",
    "password_confirm": "securepass123",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+254712345678",
    "role": "tenant"
}
```

### Properties Endpoints

#### List Properties
```http
GET /api/properties/
Authorization: Required

Response: 200 OK (filtered by user role)
[
    {
        "id": 1,
        "name": "Sunset Towers",
        "address": "123 Main St, Nairobi",
        "landlord_name": "John Landlord",
        "total_units": 12,
        ...
    }
]
```

#### Create Property (Landlords only)
```http
POST /api/properties/
Authorization: Required (Landlord)
Content-Type: application/json

{
    "name": "New Apartments",
    "address": "456 Oak Street, Nairobi",
    "description": "Modern apartments with parking"
}
```

### Units Endpoints

#### List Units
```http
GET /api/properties/units/
Authorization: Required

Response: Filtered by role
- Landlords: All units in their properties
- Caretakers: Units in managed properties
- Tenants: Only their assigned unit
```

#### Create Unit
```http
POST /api/properties/units/
Authorization: Required (Landlord/Caretaker)
Content-Type: application/json

{
    "property": 1,
    "unit_number": "A101",
    "bedrooms": 2,
    "bathrooms": 1.5,
    "rent_amount": "25000.00",
    "description": "Corner unit with balcony"
}
```

#### Assign Tenant to Unit
```http
POST /api/properties/units/{id}/assign_tenant/
Authorization: Required (Landlord/Caretaker)
Content-Type: application/json

{
    "tenant_id": 5
}
```

### Payments Endpoints

#### Record Payment
```http
POST /api/payments/
Authorization: Required (Landlord/Caretaker)
Content-Type: application/json

{
    "tenant": 1,
    "unit": 1,
    "amount": "25000.00",
    "payment_type": "rent",
    "payment_method": "cash",
    "payment_month": 11,
    "payment_year": 2024,
    "reference": "RCPT-001",
    "notes": "November rent payment"
}
```

#### Get Payment Summary
```http
GET /api/payments/summary/?month=11&year=2024
Authorization: Required (Landlord/Caretaker)

Response: Payment summary with balances
```

#### Tenant Payment History
```http
GET /api/payments/my_payments/
Authorization: Required (Tenant)

Response: Personal payment history
```

### Notices Endpoints

#### Create Notice
```http
POST /api/notices/
Authorization: Required (Landlord/Caretaker)
Content-Type: application/json

{
    "title": "Building Maintenance",
    "message": "Water will be shut off tomorrow...",
    "priority": "high",
    "audience_type": "all_tenants",
    "requires_acknowledgment": true
}
```

#### Get Tenant Notice Feed
```http
GET /api/notices/my_feed/
Authorization: Required (Tenant)

Response: Personalized notice feed (unread first)
```

#### Mark Notice as Read
```http
POST /api/notices/{id}/mark_as_read/
Authorization: Required (Tenant)

Response: 200 OK
```

## Security Features

### XSS Protection
- **HttpOnly Cookies**: JWT tokens cannot be accessed by JavaScript
- **Cookie Attributes**: Secure, SameSite=Lax for CSRF protection
- **No Token in Response Body**: Tokens never exposed to frontend code

### CSRF Protection
- **SameSite Cookies**: Prevents cross-site request forgery
- **Origin Validation**: CORS configured with specific allowed origins
- **Credentials Required**: Cookie authentication requires explicit consent

### Authentication Flow
```
1. User submits credentials
2. Backend validates and generates JWT tokens
3. Tokens set as httpOnly cookies (browser stores automatically)
4. Subsequent requests include cookies automatically
5. Backend validates tokens from cookies
6. Token refresh handled via secure cookie mechanism
```

### Password Security
- Django's built-in password hashing (PBKDF2)
- Password validation rules enforced
- Minimum length, complexity requirements

## 👥 User Roles

### Landlord
**Permissions:**
- Create/manage properties and units
- View all payments for their properties
- Create notices for tenants
- View financial reports
- Create caretaker accounts

**Cannot:**
- Be created via API (Django admin only)

### Caretaker
**Permissions:**
- Manage assigned properties
- Create/manage units
- Record payments
- Create notices
- Create tenant accounts
- Assign tenants to units

**Cannot:**
- Access properties they don't manage
- Create landlord accounts

### Tenant
**Permissions:**
- View assigned unit details
- View personal payment history
- View targeted notices
- Mark notices as read
- Update own profile

**Cannot:**
- Access other tenants' data
- Create accounts
- Modify payments or properties


## Database Schema

### Core Models

**User (accounts)**
- Custom user model extending AbstractUser
- Role field: landlord, caretaker, tenant,
- Email uniqueness constraint
- Verification status

**Property (properties)**
- Belongs to one Landlord
- Many-to-Many with Caretakers
- Has many Units

**Unit (properties)**
- Belongs to one Property
- Assigned to one Tenant (optional)
- Unique unit_number per property
- Status: available, occupied, maintenance, reserved

**Payment (payments)**
- Links Tenant and Unit
- Payment types: rent, deposit, service, late_fee, etc.
- Status tracking: pending, completed, failed
- Integration-ready for payment gateways

**Notice (notices)**
- Created by Landlord/Caretaker
- Flexible audience targeting
- Priority levels: low, normal, high, urgent
- Read status tracking

See [Database ERD](https://db) for complete schema.

## Testing

### Run Tests ##Yet to be implemented
```bash
python manage.py test 
```

### Test Coverage
```bash
pip install coverage
coverage run manage.py test
coverage report
```

### Manual API Testing

**Using cURL:**
```bash
# Login
curl -X POST http://127.0.0.1:8000/api/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}' \
  -c cookies.txt

# Authenticated request
curl -X GET http://127.0.0.1:8000/api/properties/ \
  -b cookies.txt
```

**Using Postman:**
1. Enable "Send cookies" in Postman settings
2. Login via POST to `/api/accounts/auth/login/`
3. Cookies will be stored automatically
4. Subsequent requests will include cookies

## Deployment

### Docker Deployment (Recommended)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: apartment_mgmt_db
      POSTGRES_USER: apartment_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://apartment_user:${DB_PASSWORD}@db:5432/apartment_mgmt_db

volumes:
  postgres_data:
```

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS (SSL certificates)
- [ ] Configure static files serving
- [ ] Set up database backups
- [ ] Configure logging
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Use production-grade server (Gunicorn, uWSGI)
- [ ] Configure reverse proxy (Nginx)
- [ ] Set up CI/CD pipeline

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Standards
- Follow PEP 8 style guide
- Write docstrings for all functions/classes
- Update documentation as needed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Your Name**
- GitHub: [E-ugine](https://github.com/E-ugine)
- LinkedIn: [eugine-agolla](https://www.linkedin.com/in/eugine-agolla/)
- Email: agollaeugine@gmail.com

## Acknowledgments

- Django and Django REST Framework communities
- SimpleJWT for authentication foundation
- All contributors and testers

## Support

For support, email agollaeugine@gmail.com or open an issue in the GitHub repository.

---

**Built with ❤️ using Django and Django REST Framework**