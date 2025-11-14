# Backend Setup

## Prerequisites
- Python 3.10+
- Docker and Docker Compose installed
- pip (Python package manager)

## API Setup

1. **Create a virtual environment** (recommended):
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the API server**:
   ```bash
   python -m app.main
   # Or with uvicorn directly:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
   ```

4. **Access the API**:
   - API: http://localhost:3000
   - Health check: http://localhost:3000/health
   - API docs: http://localhost:3000/docs (Swagger UI)
   - Alternative docs: http://localhost:3000/redoc

## Database Setup

### Initial Setup

1. **Create the `.env` file** (already created with default values):
   ```bash
   # The .env file contains:
   # POSTGRES_DB=mrcap_dashboard
   # POSTGRES_USER=mrcap
   # POSTGRES_PASSWORD=mrcap_dev_password
   # POSTGRES_PORT=5432
   ```

2. **Start the PostgreSQL database**:
   ```bash
   cd backend
   docker compose up -d
   ```

3. **Verify the database is running**:
   ```bash
   docker compose ps
   ```

4. **Check database logs** (optional):
   ```bash
   docker compose logs postgres
   ```

### Database Connection Details

Use these credentials to connect with DBeaver or any PostgreSQL client:

- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `mrcap_dashboard`
- **Username**: `mrcap`
- **Password**: `mrcap_dev_password`

### Schema

The database schema is automatically initialized from `db/schema.sql` when the container is first created.

### Reset Database

If you need to start fresh (⚠️ **WARNING**: This will delete all data):

```bash
docker compose down -v
docker compose up -d
```

### Stop Database

```bash
docker compose down
```

### Access Database via Command Line

```bash
docker compose exec postgres psql -U mrcap -d mrcap_dashboard
```

## API Endpoints

### Users
- `GET /api/users` - List all users (admin only)
- `GET /api/users/{id}` - Get user by ID
- `POST /api/users` - Create user (admin only)
- `PUT /api/users/{id}` - Update user (admin only)
- `DELETE /api/users/{id}` - Delete user (admin only)
- `GET /api/users/{id}/accounts` - Get user's accounts

### Movements
- `GET /api/movements/user/{user_id}` - Get all movements for a user
- `GET /api/movements/account/{account_id}` - Get all movements for an account
- `GET /api/movements/report/cash-share` - Admin report joining cash & fund share data
- `POST /api/movements/cash` - Create cash movement (admin only)
- `POST /api/movements/fund-share` - Create fund share movement (admin only)

#### Cash/Fund Share Report (Admin only)

- Endpoint: `GET /api/movements/report/cash-share`
- Auth: Bearer token for an admin user (or dev-mode admin)
- Response: Array where each row includes `user_full_name`, `user_id`, `account_number`, `account_id`, the cash movement metadata (`cash_movement_id`, `cash_movement_type`, `effective_date`, `amount`) and any linked fund share movement values (`fund_share_movement_id`, `shares_change`, `share_price`) ordered by `effective_date` ascending.

## Authentication

### Production Mode (Firebase)

The API uses Firebase Authentication. To enable:
1. Set `FIREBASE_CREDENTIALS_PATH` in `.env` pointing to your Firebase service account JSON file
2. The middleware will automatically verify Firebase ID tokens from the `Authorization: Bearer <token>` header

### Development Mode (Local Testing)

For local testing without Firebase credentials, you can use development mode:

1. Add to your `.env` file:
   ```bash
   DEV_MODE=true
   DEV_USER_ID=1  # ID of a user in your database
   ```

2. The API will automatically use the specified user ID for all requests (no token required)

**⚠️ WARNING**: Never enable `DEV_MODE` in production! This bypasses all authentication.

### Creating a Test User

To create a test user for dev mode, you can use the database directly:

```bash
make db-shell
```

Then in psql:
```sql
INSERT INTO app_users (firebase_uid, email, full_name, is_admin, status)
VALUES ('dev-user-123', 'test@example.com', 'Test User', true, 'active')
RETURNING id;
```

Use the returned `id` as your `DEV_USER_ID`.

