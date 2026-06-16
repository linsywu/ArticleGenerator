## ADDED Requirements

### Requirement: User authentication via JWT
The system SHALL authenticate users via username/password and issue a JWT access token valid for a configurable duration. The system SHALL protect all API endpoints except `/api/health` and `/api/auth/login` with Bearer token validation.

#### Scenario: Successful login
- **WHEN** a user sends valid credentials to POST /api/auth/login
- **THEN** the system returns a JWT access token with type "bearer"

#### Scenario: Failed login
- **WHEN** a user sends invalid credentials to POST /api/auth/login
- **THEN** the system returns HTTP 401 with an error message

#### Scenario: Unauthenticated access
- **WHEN** a request without a valid Bearer token accesses any protected endpoint
- **THEN** the system returns HTTP 401

#### Scenario: Expired token
- **WHEN** a request uses an expired JWT token
- **THEN** the system returns HTTP 401

### Requirement: Seed user creation
The system SHALL automatically create a seed administrator user from environment variables if no users exist in the database at startup.

#### Scenario: First startup with no users
- **WHEN** the application starts and the users table is empty
- **THEN** a user is created using SEED_USERNAME and SEED_PASSWORD from .env

#### Scenario: Subsequent startup with existing users
- **WHEN** the application starts and users already exist
- **THEN** no duplicate seed user is created

### Requirement: Frontend login page
The frontend SHALL provide a login page that authenticates users and stores the JWT token. The router SHALL redirect unauthenticated users to the login page.

#### Scenario: User accesses app without token
- **WHEN** a user navigates to any route without a stored JWT token
- **THEN** the router redirects to /login

#### Scenario: User logs in successfully
- **WHEN** a user submits valid credentials on the login page
- **THEN** the token is stored in localStorage and the user is redirected to the main page

#### Scenario: 401 response clears token
- **WHEN** any API request receives a 401 response
- **THEN** the stored token is cleared and the user is redirected to /login
