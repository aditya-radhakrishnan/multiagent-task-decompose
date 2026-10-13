# Independent Agents Approach

Duration: 126.18s
Cost: $0.1589

## API Designer

# API Contract: GET /api/user/preferences

## Endpoint Overview
Retrieves user-specific preference settings including UI customization, notification settings, and application behavior configurations.

## Endpoint Details

**URL:** `/api/user/preferences`  
**Method:** `GET`  
**Content-Type:** `application/json`

---

## Authentication

**Type:** Bearer Token (JWT)

**Header:**
```
Authorization: Bearer <access_token>
```

**Requirements:**
- Valid JWT token required
- Token must not be expired
- User must have an active account status

---

## Request Format

### Headers
```http
GET /api/user/preferences HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: application/json
```

### Query Parameters (Optional)

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `categories` | string | No | Comma-separated list of preference categories to retrieve | `ui,notifications` |
| `include_defaults` | boolean | No | Include default values for unset preferences | `true` |

**Example Requests:**
```
GET /api/user/preferences
GET /api/user/preferences?categories=ui,notifications
GET /api/user/preferences?include_defaults=true
```

---

## Response Format

### Success Response (200 OK)

```json
{
  "status": "success",
  "data": {
    "user_id": "usr_123456789",
    "preferences": {
      "ui": {
        "theme": "dark",
        "language": "en-US",
        "timezone": "America/New_York",
        "date_format": "MM/DD/YYYY",
        "time_format": "12h",
        "sidebar_collapsed": false,
        "items_per_page": 25
      },
      "notifications": {
        "email_enabled": true,
        "push_enabled": false,
        "sms_enabled": false,
        "frequency": "daily",
        "quiet_hours": {
          "enabled": true,
          "start": "22:00",
          "end": "08:00"
        },
        "categories": {
          "security_alerts": true,
          "product_updates": true,
          "marketing": false,
          "social": true
        }
      },
      "privacy": {
        "profile_visibility": "private",
        "show_online_status": false,
        "allow_search_indexing": false,
        "data_sharing": false
      },
      "accessibility": {
        "high_contrast": false,
        "screen_reader_optimized": false,
        "reduce_motion": false,
        "font_size": "medium"
      }
    },
    "last_updated": "2024-01-15T10:30:00Z",
    "version": "1.2"
  },
  "meta": {
    "timestamp": "2024-01-15T14:25:30Z",
    "request_id": "req_abc123xyz"
  }
}
```

### Response Fields Description

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Response status indicator |
| `data.user_id` | string | Unique identifier for the user |
| `data.preferences` | object | Nested object containing all preference categories |
| `data.last_updated` | string (ISO 8601) | Timestamp of last preference modification |
| `data.version` | string | Preference schema version |
| `meta.timestamp` | string (ISO 8601) | Server response timestamp |
| `meta.request_id` | string | Unique request identifier for tracking |

---

## Error Responses

### 401 Unauthorized
**When:** Missing, invalid, or expired authentication token

```json
{
  "status": "error",
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required",
    "details": "The access token is missing or invalid"
  },
  "meta": {
    "timestamp": "2024-01-15T14:25:30Z",
    "request_id": "req_abc123xyz"
  }
}
```

### 403 Forbidden
**When:** Valid token but insufficient permissions

```json
{
  "status": "error",
  "error": {
    "code": "FORBIDDEN",
    "message": "Access denied",
    "details": "User account is suspended or lacks necessary permissions"
  },
  "meta": {
    "timestamp": "2024-01-15T14:25:30Z",
    "request_id": "req_abc123xyz"
  }
}
```

### 404 Not Found
**When:** User preferences not initialized

```json
{
  "status": "error",
  "error": {
    "code": "NOT_FOUND",
    "message": "Preferences not found",
    "details": "No preferences have been set for this user"
  },
  "meta": {
    "timestamp": "2024-01-15T14:25:30Z",
    "request_id": "req_abc123xyz"
  }
}
```

### 400 Bad Request
**When:** Invalid query parameters

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid request parameters",
    "details": "The category 'invalid_cat' is not recognized",
    "invalid_fields": ["categories"]
  },
  "meta": {
    "timestamp": "2024-01-15T14:25:30Z",
    "request_id": "req_abc123xyz"
  }
}
```

### 429 Too Many Requests
**When:** Rate limit exceeded

```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": "Rate limit of 100 requests per minute exceeded"
  },
  "meta": {
    "timestamp": "2024-01-15T14:25:30Z",
    "request_id": "req_abc123xyz",
    "retry_after": 45
  }
}
```

### 500 Internal Server Error
**When:** Server-side error occurs

```json
{
  "status": "error",
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An internal server error occurred",
    "details": "Please try again later or contact support"
  },
  "meta": {
    "timestamp": "2024-01-15T14:25:30Z",
    "request_id": "req_abc123xyz"
  }
}
```

### 503 Service Unavailable
**When:** Service is temporarily unavailable

```json
{
  "status": "error",
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Service temporarily unavailable",
    "details": "The service is undergoing maintenance"
  },
  "meta": {
    "timestamp": "2024-01-15T14:25:30Z",
    "request_id": "req_abc123xyz",
    "retry_after": 300
  }
}
```

---

## Rate Limiting

- **Limit:** 100 requests per minute per user
- **Headers Included:**
  - `X-RateLimit-Limit: 100`
  - `X-RateLimit-Remaining: 95`
  - `X-RateLimit-Reset: 1705329930`

---

## Caching

- **Cache-Control:** `private, max-age=300`
- **ETag:** Supported for conditional requests
- Clients should cache responses and use `If-None-Match` header for subsequent requests

**Example:**
```http
GET /api/user/preferences HTTP/1.1
If-None-Match: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

**304 Not Modified Response:**
```http
HTTP/1.1 304 Not Modified
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
Cache-Control: private, max-age=300
```

---

## Example Usage

### cURL
```bash
curl -X GET "https://api.example.com/api/user/preferences" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

### JavaScript (Fetch)
```javascript
fetch('https://api.example.com/api/user/preferences', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
    'Accept': 'application/json'
  }
})
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

### Python (Requests)
```python
import requests

url = "https://api.example.com/api/user/preferences"
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)
data = response.json()
print(data)
```

---

## Related Endpoints

- `PATCH /api/user/preferences` - Update user preferences
- `PUT /api/user/preferences` - Replace all user preferences
- `DELETE /api/user/preferences` - Reset preferences to defaults
- `GET /api/user/preferences/schema` - Get preference schema and validation rules

---

## Versioning

**Current Version:** v1  
**Version Header:** `API-Version: 1`

Future versions will be accessible via URL versioning:
- v1: `/api/user/preferences` (current)
- v2: `/api/v2/user/preferences` (future)

---

## Notes

1. All timestamps are in UTC and follow ISO 8601 format
2. Preference categories may expand in future versions
3. Unset preferences will use system defaults unless `include_defaults=false`
4. The `request_id` should be logged and provided when reporting issues
5. Clients should implement exponential backoff for rate limit errors

## Backend Developer

# Flask Backend: User Preferences API

Here's a complete implementation with authentication, error handling, and best practices:

```python
# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import wraps
import jwt
from datetime import datetime, timedelta
import os
from typing import Dict, Any, Optional
import logging

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_EXPIRATION_HOURS'] = 24

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock database (replace with actual database in production)
USERS_DB = {
    "user123": {
        "id": "user123",
        "username": "john_doe",
        "email": "john@example.com",
        "preferences": {
            "theme": "dark",
            "language": "en",
            "timezone": "America/New_York",
            "notifications": {
                "email": True,
                "push": False,
                "sms": False,
                "in_app": True
            }
        }
    },
    "user456": {
        "id": "user456",
        "username": "jane_smith",
        "email": "jane@example.com",
        "preferences": {
            "theme": "light",
            "language": "es",
            "timezone": "Europe/Madrid",
            "notifications": {
                "email": True,
                "push": True,
                "sms": True,
                "in_app": True
            }
        }
    }
}

# Default preferences for new users
DEFAULT_PREFERENCES = {
    "theme": "light",
    "language": "en",
    "timezone": "UTC",
    "notifications": {
        "email": True,
        "push": True,
        "sms": False,
        "in_app": True
    }
}

# Supported values for validation
VALID_THEMES = ["light", "dark", "auto"]
VALID_LANGUAGES = ["en", "es", "fr", "de", "it", "pt", "zh", "ja"]
VALID_TIMEZONES = [
    "UTC", "America/New_York", "America/Chicago", "America/Los_Angeles",
    "Europe/London", "Europe/Paris", "Europe/Madrid", "Asia/Tokyo",
    "Asia/Shanghai", "Australia/Sydney"
]

# ====================== Authentication Decorator ======================

def token_required(f):
    """
    Decorator to protect routes with JWT authentication
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Expected format: "Bearer <token>"
                token = auth_header.split(" ")[1] if " " in auth_header else auth_header
            except IndexError:
                logger.warning("Malformed Authorization header")
                return jsonify({
                    'success': False,
                    'error': 'Invalid authorization header format',
                    'message': 'Expected format: Bearer <token>'
                }), 401
        
        if not token:
            logger.warning("Authentication attempted without token")
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'message': 'Access token is missing'
            }), 401
        
        try:
            # Decode and verify token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
            
            # Verify user exists
            if current_user_id not in USERS_DB:
                logger.warning(f"Token valid but user not found: {current_user_id}")
                return jsonify({
                    'success': False,
                    'error': 'User not found',
                    'message': 'The user associated with this token no longer exists'
                }), 404
            
            # Attach user to request context
            request.current_user = USERS_DB[current_user_id]
            
        except jwt.ExpiredSignatureError:
            logger.info("Expired token used")
            return jsonify({
                'success': False,
                'error': 'Token expired',
                'message': 'Your session has expired. Please login again'
            }), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Invalid token',
                'message': 'The provided token is invalid'
            }), 401
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Authentication error',
                'message': 'An error occurred during authentication'
            }), 500
        
        return f(*args, **kwargs)
    
    return decorated

# ====================== API Routes ======================

@app.route('/api/user/preferences', methods=['GET'])
@token_required
def get_user_preferences():
    """
    GET /api/user/preferences
    
    Returns the current user's preferences including theme, language, 
    timezone, and notification settings.
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: Success with preferences data
        401: Unauthorized (missing or invalid token)
        404: User preferences not found
        500: Internal server error
    """
    try:
        user = request.current_user
        user_id = user['id']
        
        logger.info(f"Fetching preferences for user: {user_id}")
        
        # Get user preferences or return defaults
        preferences = user.get('preferences', DEFAULT_PREFERENCES.copy())
        
        # Ensure all required fields exist
        if not preferences:
            logger.warning(f"No preferences found for user {user_id}, using defaults")
            preferences = DEFAULT_PREFERENCES.copy()
        
        # Build response
        response_data = {
            'success': True,
            'data': {
                'user_id': user_id,
                'preferences': {
                    'theme': preferences.get('theme', DEFAULT_PREFERENCES['theme']),
                    'language': preferences.get('language', DEFAULT_PREFERENCES['language']),
                    'timezone': preferences.get('timezone', DEFAULT_PREFERENCES['timezone']),
                    'notifications': preferences.get('notifications', DEFAULT_PREFERENCES['notifications'])
                }
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        logger.info(f"Successfully retrieved preferences for user: {user_id}")
        return jsonify(response_data), 200
        
    except KeyError as e:
        logger.error(f"Missing required field: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Data structure error',
            'message': f'Missing required field: {str(e)}'
        }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get_user_preferences: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while fetching preferences'
        }), 500

@app.route('/api/user/preferences', methods=['PUT', 'PATCH'])
@token_required
def update_user_preferences():
    """
    PUT/PATCH /api/user/preferences
    
    Updates user preferences. PUT replaces all preferences, 
    PATCH updates only provided fields.
    
    Headers:
        Authorization: Bearer <token>
        Content-Type: application/json
    
    Body:
        {
            "theme": "dark",
            "language": "en",
            "timezone": "America/New_York",
            "notifications": {
                "email": true,
                "push": false,
                "sms": false,
                "in_app": true
            }
        }
    """
    try:
        user = request.current_user
        user_id = user['id']
        
        # Validate content type
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Invalid content type',
                'message': 'Content-Type must be application/json'
            }), 415
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Empty request body',
                'message': 'Request body cannot be empty'
            }), 400
        
        # Get current preferences
        current_prefs = user.get('preferences', DEFAULT_PREFERENCES.copy())
        
        # Validate and update preferences
        errors = []
        
        if 'theme' in data:
            if data['theme'] not in VALID_THEMES:
                errors.append(f"Invalid theme. Must be one of: {', '.join(VALID_THEMES)}")
            else:
                current_prefs['theme'] = data['theme']
        
        if 'language' in data:
            if data['language'] not in VALID_LANGUAGES:
                errors.append(f"Invalid language. Must be one of: {', '.join(VALID_LANGUAGES)}")
            else:
                current_prefs['language'] = data['language']
        
        if 'timezone' in data:
            if data['timezone'] not in VALID_TIMEZONES:
                errors.append(f"Invalid timezone. Must be one of: {', '.join(VALID_TIMEZONES)}")
            else:
                current_prefs['timezone'] = data['timezone']
        
        if 'notifications' in data:
            if not isinstance(data['notifications'], dict):
                errors.append("Notifications must be an object")
            else:
                current_prefs['notifications'].update(data['notifications'])
        
        if errors:
            return jsonify({
                'success': False,
                'error': 'Validation error',
                'message': 'Invalid preference values',
                'details': errors
            }), 400
        
        # Update user preferences in database
        USERS_DB[user_id]['preferences'] = current_prefs
        
        logger.info(f"Successfully updated preferences for user: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Preferences updated successfully',
            'data': {
                'preferences': current_prefs
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while updating preferences'
        }), 500

# ====================== Helper Routes for Testing ======================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Mock login endpoint for testing
    
    Body:
        {
            "username": "john_doe",
            "password": "password123"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'username' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing credentials',
                'message': 'Username is required'
            }), 400
        
        # Find user by username (simplified for demo)
        user = None
        for uid, u in USERS_DB.items():
            if u['username'] == data['username']:
                user = u
                break
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid credentials',
                'message': 'Username or password is incorrect'
            }), 401
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'exp': datetime.utcnow() + timedelta(hours=app.config['JWT_EXPIRATION_HOURS'])
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        logger.info(f"User logged in: {user['username']}")
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'data': {
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email']
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An error occurred during login'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200

# ====================== Error Handlers ======================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        'success': False,
        'error': 'Method not allowed',
        'message': f'The {request.method} method is not allowed for this endpoint'
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

# ====================== Main ======================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

```python
# requirements.txt
Flask==3.0.0
Flask-CORS==4.0.0
PyJWT==2.8.0
python-dotenv==1.0.0
```

```python
# test_api.py
"""
Test script for the User Preferences API
Run: python test_api.py
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_api():
    print("=" * 60)
    print("Testing User Preferences API")
    print("=" * 60)
    
    # 1. Test login to get token
    print("\n1. Testing Login...")
    login_data = {
        "username": "john_doe",
        "password": "password123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code != 200:
        print("Login failed! Cannot continue tests.")
        return
    
    token = response.json()['data']['token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Test GET preferences
    print("\n2. Testing GET /api/user/preferences...")
    response = requests.get(f"{

## Frontend Developer

# API Client for GET /api/user/preferences

Here's a complete TypeScript implementation with authentication, response parsing, and comprehensive error handling:

```typescript
// types.ts
export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  notifications: {
    email: boolean;
    push: boolean;
    sms: boolean;
  };
  timezone: string;
  dateFormat: string;
  [key: string]: any; // Allow for additional properties
}

export interface ApiError {
  message: string;
  code?: string;
  statusCode: number;
  details?: any;
}

export class PreferencesApiError extends Error {
  constructor(
    public statusCode: number,
    public code?: string,
    public details?: any
  ) {
    super(`API Error: ${statusCode}`);
    this.name = 'PreferencesApiError';
  }
}

// config.ts
export interface ApiConfig {
  baseUrl: string;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
}

export const defaultConfig: ApiConfig = {
  baseUrl: process.env.API_BASE_URL || 'https://api.example.com',
  timeout: 10000,
  retryAttempts: 3,
  retryDelay: 1000,
};

// authManager.ts
export interface AuthToken {
  access_token: string;
  token_type?: string;
  expires_at?: number;
}

export class AuthManager {
  private token: AuthToken | null = null;
  private tokenKey = 'auth_token';

  setToken(token: AuthToken): void {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem(this.tokenKey, JSON.stringify(token));
    }
  }

  getToken(): AuthToken | null {
    if (this.token) {
      return this.token;
    }

    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(this.tokenKey);
      if (stored) {
        try {
          this.token = JSON.parse(stored);
          return this.token;
        } catch {
          this.clearToken();
        }
      }
    }

    return null;
  }

  isTokenExpired(): boolean {
    const token = this.getToken();
    if (!token || !token.expires_at) {
      return false;
    }
    return Date.now() >= token.expires_at;
  }

  clearToken(): void {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem(this.tokenKey);
    }
  }

  getAuthHeader(): string | null {
    const token = this.getToken();
    if (!token) {
      return null;
    }

    const tokenType = token.token_type || 'Bearer';
    return `${tokenType} ${token.access_token}`;
  }
}

// preferencesClient.ts
export class PreferencesClient {
  private config: ApiConfig;
  private authManager: AuthManager;

  constructor(config: Partial<ApiConfig> = {}, authManager?: AuthManager) {
    this.config = { ...defaultConfig, ...config };
    this.authManager = authManager || new AuthManager();
  }

  /**
   * Fetch user preferences from the API
   */
  async getUserPreferences(): Promise<UserPreferences> {
    const url = `${this.config.baseUrl}/api/user/preferences`;
    
    try {
      const response = await this.fetchWithRetry(url);
      return this.parseResponse<UserPreferences>(response);
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Make HTTP request with retry logic
   */
  private async fetchWithRetry(
    url: string,
    attempt: number = 1
  ): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      this.config.timeout
    );

    try {
      const headers = this.buildHeaders();
      
      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: controller.signal,
        credentials: 'include', // Include cookies if needed
      });

      clearTimeout(timeoutId);

      // Check if we need to retry
      if (this.shouldRetry(response.status, attempt)) {
        await this.delay(this.config.retryDelay! * attempt);
        return this.fetchWithRetry(url, attempt + 1);
      }

      return response;
    } catch (error) {
      clearTimeout(timeoutId);

      // Retry on network errors
      if (
        attempt < this.config.retryAttempts! &&
        this.isRetryableError(error)
      ) {
        await this.delay(this.config.retryDelay! * attempt);
        return this.fetchWithRetry(url, attempt + 1);
      }

      throw error;
    }
  }

  /**
   * Build request headers including authentication
   */
  private buildHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    // Add authentication header
    const authHeader = this.authManager.getAuthHeader();
    if (authHeader) {
      headers['Authorization'] = authHeader;
    }

    return headers;
  }

  /**
   * Parse and validate API response
   */
  private async parseResponse<T>(response: Response): Promise<T> {
    // Handle successful responses
    if (response.ok) {
      const contentType = response.headers.get('content-type');
      
      if (contentType?.includes('application/json')) {
        const data = await response.json();
        return this.validatePreferences(data) as T;
      }
      
      throw new PreferencesApiError(
        response.status,
        'INVALID_CONTENT_TYPE',
        'Expected JSON response'
      );
    }

    // Handle error responses
    await this.handleErrorResponse(response);
    
    // This line should never be reached, but TypeScript requires it
    throw new PreferencesApiError(response.status);
  }

  /**
   * Validate preferences data structure
   */
  private validatePreferences(data: any): UserPreferences {
    if (!data || typeof data !== 'object') {
      throw new PreferencesApiError(
        200,
        'INVALID_RESPONSE',
        'Response is not a valid object'
      );
    }

    // Basic validation - adjust based on your requirements
    const preferences: UserPreferences = {
      theme: data.theme || 'light',
      language: data.language || 'en',
      notifications: {
        email: data.notifications?.email ?? true,
        push: data.notifications?.push ?? false,
        sms: data.notifications?.sms ?? false,
      },
      timezone: data.timezone || 'UTC',
      dateFormat: data.dateFormat || 'YYYY-MM-DD',
      ...data, // Include any additional properties
    };

    return preferences;
  }

  /**
   * Handle HTTP error responses
   */
  private async handleErrorResponse(response: Response): Promise<never> {
    let errorData: any = null;
    
    try {
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        errorData = await response.json();
      } else {
        errorData = await response.text();
      }
    } catch {
      // Ignore parsing errors
    }

    const errorCode = errorData?.code || errorData?.error;
    const errorMessage = errorData?.message || response.statusText;

    switch (response.status) {
      case 401:
        this.authManager.clearToken();
        throw new PreferencesApiError(
          401,
          errorCode || 'UNAUTHORIZED',
          errorMessage || 'Authentication required'
        );

      case 403:
        throw new PreferencesApiError(
          403,
          errorCode || 'FORBIDDEN',
          errorMessage || 'Access denied'
        );

      case 404:
        throw new PreferencesApiError(
          404,
          errorCode || 'NOT_FOUND',
          errorMessage || 'Preferences not found'
        );

      case 429:
        throw new PreferencesApiError(
          429,
          errorCode || 'RATE_LIMITED',
          errorMessage || 'Too many requests'
        );

      case 500:
      case 502:
      case 503:
      case 504:
        throw new PreferencesApiError(
          response.status,
          errorCode || 'SERVER_ERROR',
          errorMessage || 'Server error occurred'
        );

      default:
        throw new PreferencesApiError(
          response.status,
          errorCode || 'UNKNOWN_ERROR',
          errorMessage || 'An unexpected error occurred'
        );
    }
  }

  /**
   * Generic error handler
   */
  private handleError(error: any): Error {
    if (error instanceof PreferencesApiError) {
      return error;
    }

    if (error.name === 'AbortError') {
      return new PreferencesApiError(
        408,
        'TIMEOUT',
        `Request timeout after ${this.config.timeout}ms`
      );
    }

    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      return new PreferencesApiError(
        0,
        'NETWORK_ERROR',
        'Network error - please check your connection'
      );
    }

    return new PreferencesApiError(
      0,
      'UNKNOWN_ERROR',
      error.message || 'An unexpected error occurred'
    );
  }

  /**
   * Determine if the request should be retried
   */
  private shouldRetry(status: number, attempt: number): boolean {
    if (attempt >= this.config.retryAttempts!) {
      return false;
    }

    // Retry on server errors and rate limiting
    return status === 429 || status >= 500;
  }

  /**
   * Check if error is retryable
   */
  private isRetryableError(error: any): boolean {
    return (
      error.name === 'AbortError' ||
      error.message === 'Failed to fetch' ||
      error.message.includes('network')
    );
  }

  /**
   * Delay utility for retries
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Set authentication token
   */
  setAuthToken(token: AuthToken): void {
    this.authManager.setToken(token);
  }

  /**
   * Clear authentication token
   */
  clearAuthToken(): void {
    this.authManager.clearToken();
  }
}

// Usage example
export const createPreferencesClient = (
  config?: Partial<ApiConfig>
): PreferencesClient => {
  return new PreferencesClient(config);
};
```

## Usage Examples

```typescript
// example.ts

// 1. Basic usage
import { PreferencesClient } from './preferencesClient';

const client = new PreferencesClient({
  baseUrl: 'https://api.example.com',
  timeout: 5000,
});

// Set authentication token
client.setAuthToken({
  access_token: 'your-jwt-token-here',
  token_type: 'Bearer',
  expires_at: Date.now() + 3600000, // 1 hour from now
});

// Fetch preferences
async function loadPreferences() {
  try {
    const preferences = await client.getUserPreferences();
    console.log('User preferences:', preferences);
    
    // Use the preferences
    document.body.className = preferences.theme;
    console.log(`Language: ${preferences.language}`);
    console.log(`Email notifications: ${preferences.notifications.email}`);
    
  } catch (error) {
    if (error instanceof PreferencesApiError) {
      console.error(`Error ${error.statusCode}:`, error.message);
      
      if (error.statusCode === 401) {
        // Redirect to login
        window.location.href = '/login';
      } else if (error.statusCode === 404) {
        // Initialize with default preferences
        console.log('No preferences found, using defaults');
      }
    } else {
      console.error('Unexpected error:', error);
    }
  }
}

// 2. With React Hook
import { useState, useEffect } from 'react';

function useUserPreferences() {
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const client = new PreferencesClient();
    
    client.getUserPreferences()
      .then(setPreferences)
      .catch(err => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return { preferences, loading, error };
}

// Component usage
function PreferencesDisplay() {
  const { preferences, loading, error } = useUserPreferences();

  if (loading) return <div>Loading preferences...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!preferences) return null;

  return (
    <div>
      <h2>Your Preferences</h2>
      <p>Theme: {preferences.theme}</p>
      <p>Language: {preferences.language}</p>
      <p>Timezone: {preferences.timezone}</p>
    </div>
  );
}

// 3. With async/await and error handling
async function fetchAndApplyPreferences() {
  const client = new PreferencesClient();
  
  try {
    const prefs = await client.getUserPreferences();
    
    // Apply theme
    applyTheme(prefs.theme);
    
    // Set language
    setLanguage(prefs.language);
    
    return prefs;
    
  } catch (error) {
    if (error instanceof PreferencesApiError) {
      switch (error.statusCode) {
        case 401:
          handleUnauthorized();
          break;
        case 403:
          handleForbidden();
          break;
        case 404:
          return getDefaultPreferences();
        case 429:
          showRateLimitMessage();
          break;
        default:
          showGenericError(error.message);
      }
    }
    throw error;
  }
}

// 4. With retry and custom configuration
const client = new PreferencesClient({
  baseUrl: process.env.REACT_APP_API_URL,
  timeout: 15000,
  retryAttempts: 5,
  retryDelay: 2000,
});

// Set token from OAuth callback
const token = new URLSearchParams(window.location.search).get('token');
if (token) {
  client.setAuthToken({ access_token: token });
}
```

## Testing

```typescript
// preferencesClient.test.ts
import { PreferencesClient, PreferencesApiError } from './preferencesClient';

describe('PreferencesClient', () => {
  let client: PreferencesClient;
  let fetchMock: jest.Mock;

  beforeEach(() => {
    fetchMock = jest.fn();
    global.fetch = fetchMock;
    
    client = new PreferencesClient({
      baseUrl: 'https://api.test.com',
      retryAttempts: 2,
      retryDelay: 100,
    });
  

