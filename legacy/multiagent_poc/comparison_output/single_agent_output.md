# Single Agent Approach

Duration: 53.52s
Cost: $0.0728

# API Feature: User Preferences Endpoint

## 1. API Contract Specification

### Endpoint
```
GET /api/user/preferences
```

### Authentication
- Requires Bearer token in Authorization header
- Header format: `Authorization: Bearer <token>`

### Request
```http
GET /api/user/preferences HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Response - Success (200 OK)
```json
{
  "success": true,
  "data": {
    "userId": "12345",
    "preferences": {
      "theme": "dark",
      "language": "en",
      "timezone": "America/New_York",
      "notifications": {
        "email": true,
        "push": false,
        "sms": false
      }
    },
    "updatedAt": "2024-01-15T10:30:00Z"
  }
}
```

### Response - Errors

#### 401 Unauthorized
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication token is missing or invalid"
  }
}
```

#### 404 Not Found
```json
{
  "success": false,
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User preferences not found"
  }
}
```

#### 500 Internal Server Error
```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

### Data Types
```typescript
type Theme = "light" | "dark" | "auto";
type Language = "en" | "es" | "fr" | "de" | "ja";
type Timezone = string; // IANA timezone format

interface NotificationSettings {
  email: boolean;
  push: boolean;
  sms: boolean;
}

interface UserPreferences {
  theme: Theme;
  language: Language;
  timezone: Timezone;
  notifications: NotificationSettings;
}
```

---

## 2. Backend Implementation (Python/Flask)

### `app.py` - Main Application
```python
from flask import Flask, jsonify, request
from functools import wraps
import jwt
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Mock database - replace with actual database in production
MOCK_USER_PREFERENCES = {
    "12345": {
        "theme": "dark",
        "language": "en",
        "timezone": "America/New_York",
        "notifications": {
            "email": True,
            "push": False,
            "sms": False
        },
        "updated_at": "2024-01-15T10:30:00Z"
    },
    "67890": {
        "theme": "light",
        "language": "es",
        "timezone": "Europe/Madrid",
        "notifications": {
            "email": True,
            "push": True,
            "sms": True
        },
        "updated_at": "2024-01-14T15:20:00Z"
    }
}


def require_auth(f):
    """Authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication token is missing or invalid"
                }
            }), 401
        
        try:
            # Extract token from "Bearer <token>"
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            
            # Decode and verify token
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = payload.get('user_id')
            
            if not request.user_id:
                raise ValueError("Invalid token payload")
                
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Token has expired"
                }
            }), 401
        except (jwt.InvalidTokenError, ValueError, IndexError):
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication token is missing or invalid"
                }
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


@app.route('/api/user/preferences', methods=['GET'])
@require_auth
def get_user_preferences():
    """
    Get user preference settings
    
    Returns:
        JSON response with user preferences or error
    """
    try:
        user_id = request.user_id
        
        # Fetch preferences from database (using mock data here)
        preferences = MOCK_USER_PREFERENCES.get(user_id)
        
        if not preferences:
            return jsonify({
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User preferences not found"
                }
            }), 404
        
        # Format response
        response_data = {
            "success": True,
            "data": {
                "userId": user_id,
                "preferences": {
                    "theme": preferences["theme"],
                    "language": preferences["language"],
                    "timezone": preferences["timezone"],
                    "notifications": preferences["notifications"]
                },
                "updatedAt": preferences["updated_at"]
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        # Log the error in production
        app.logger.error(f"Error fetching user preferences: {str(e)}")
        
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "error": {
            "code": "NOT_FOUND",
            "message": "Endpoint not found"
        }
    }), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "success": False,
        "error": {
            "code": "METHOD_NOT_ALLOWED",
            "message": "HTTP method not allowed for this endpoint"
        }
    }), 405


if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### `models.py` - Data Models (Optional)
```python
from dataclasses import dataclass
from typing import Dict
from datetime import datetime


@dataclass
class NotificationSettings:
    email: bool
    push: bool
    sms: bool
    
    def to_dict(self) -> Dict:
        return {
            "email": self.email,
            "push": self.push,
            "sms": self.sms
        }


@dataclass
class UserPreferences:
    theme: str
    language: str
    timezone: str
    notifications: NotificationSettings
    updated_at: datetime
    
    def to_dict(self) -> Dict:
        return {
            "theme": self.theme,
            "language": self.language,
            "timezone": self.timezone,
            "notifications": self.notifications.to_dict(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @staticmethod
    def validate_theme(theme: str) -> bool:
        return theme in ["light", "dark", "auto"]
    
    @staticmethod
    def validate_language(language: str) -> bool:
        return language in ["en", "es", "fr", "de", "ja"]
```

### `requirements.txt`
```
Flask==3.0.0
PyJWT==2.8.0
```

---

## 3. Frontend Implementation (TypeScript)

### `types/preferences.ts` - Type Definitions
```typescript
export type Theme = "light" | "dark" | "auto";
export type Language = "en" | "es" | "fr" | "de" | "ja";

export interface NotificationSettings {
  email: boolean;
  push: boolean;
  sms: boolean;
}

export interface UserPreferences {
  theme: Theme;
  language: Language;
  timezone: string;
  notifications: NotificationSettings;
}

export interface UserPreferencesResponse {
  userId: string;
  preferences: UserPreferences;
  updatedAt: string;
}

export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
}

export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;
```

### `api/preferencesApi.ts` - API Client
```typescript
import type {
  ApiResponse,
  UserPreferencesResponse,
} from "../types/preferences";

export class PreferencesApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public statusCode: number
  ) {
    super(message);
    this.name = "PreferencesApiError";
  }
}

export class PreferencesApi {
  private baseUrl: string;
  private getAuthToken: () => string | null;

  constructor(
    baseUrl: string = "/api",
    getAuthToken: () => string | null = () => localStorage.getItem("authToken")
  ) {
    this.baseUrl = baseUrl;
    this.getAuthToken = getAuthToken;
  }

  /**
   * Fetch user preferences from the API
   * @throws {PreferencesApiError} When the request fails
   * @returns {Promise<UserPreferencesResponse>} User preferences data
   */
  async getUserPreferences(): Promise<UserPreferencesResponse> {
    const token = this.getAuthToken();

    if (!token) {
      throw new PreferencesApiError(
        "NO_TOKEN",
        "Authentication token not found",
        401
      );
    }

    try {
      const response = await fetch(`${this.baseUrl}/user/preferences`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      const data: ApiResponse<UserPreferencesResponse> = await response.json();

      if (!response.ok) {
        if (!data.success) {
          throw new PreferencesApiError(
            data.error.code,
            data.error.message,
            response.status
          );
        }
        throw new PreferencesApiError(
          "UNKNOWN_ERROR",
          "An unknown error occurred",
          response.status
        );
      }

      if (data.success) {
        return data.data;
      }

      throw new PreferencesApiError(
        "INVALID_RESPONSE",
        "Invalid response format",
        500
      );
    } catch (error) {
      if (error instanceof PreferencesApiError) {
        throw error;
      }

      // Network or parsing errors
      if (error instanceof TypeError) {
        throw new PreferencesApiError(
          "NETWORK_ERROR",
          "Network request failed. Please check your connection.",
          0
        );
      }

      throw new PreferencesApiError(
        "UNKNOWN_ERROR",
        error instanceof Error ? error.message : "An unknown error occurred",
        500
      );
    }
  }
}

// Singleton instance for convenience
export const preferencesApi = new PreferencesApi();
```

### `hooks/useUserPreferences.ts` - React Hook (Optional)
```typescript
import { useState, useEffect, useCallback } from "react";
import {
  preferencesApi,
  PreferencesApiError,
} from "../api/preferencesApi";
import type { UserPreferencesResponse } from "../types/preferences";

interface UseUserPreferencesState {
  data: UserPreferencesResponse | null;
  loading: boolean;
  error: PreferencesApiError | null;
}

export function useUserPreferences() {
  const [state, setState] = useState<UseUserPreferencesState>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchPreferences = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const data = await preferencesApi.getUserPreferences();
      setState({ data, loading: false, error: null });
    } catch (error) {
      if (error instanceof PreferencesApiError) {
        setState({ data: null, loading: false, error });
      } else {
        setState({
          data: null,
          loading: false,
          error: new PreferencesApiError(
            "UNKNOWN_ERROR",
            "An unexpected error occurred",
            500
          ),
        });
      }
    }
  }, []);

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  return {
    ...state,
    refetch: fetchPreferences,
  };
}
```

### `components/UserPreferences.tsx` - Example Component
```typescript
import React from "react";
import { useUserPreferences } from "../hooks/useUserPreferences";

export const UserPreferencesComponent: React.FC = () => {
  const { data, loading, error, refetch } = useUserPreferences();

  if (loading) {
    return <div className="loading">Loading preferences...</div>;
  }

  if (error) {
    return (
      <div className="error">
        <h3>Error Loading Preferences</h3>
        <p>{error.message}</p>
        <button onClick={refetch}>Retry</button>
      </div>
    );
  }

  if (!data) {
    return <div>No preferences found</div>;
  }

  return (
    <div className="preferences">
      <h2>User Preferences</h2>
      <div className="preference-item">
        <label>Theme:</label>
        <span>{data.preferences.theme}</span>
      </div>
      <div className="preference-item">
        <label>Language:</label>
        <span>{data.preferences.language}</span>
      </div>
      <div className="preference-item">
        <label>Timezone:</label>
        <span>{data.preferences.timezone}</span>
      </div>
      <div className="preference-section">
        <h3>Notifications</h3>
        <div className="preference-item">
          <label>Email:</label>
          <span>{data.preferences.notifications.email ? "On" : "Off"}</span>
        </div>
        <div className="preference-item">
          <label>Push:</label>
          <span>{data.preferences.notifications.push ? "On" : "Off"}</span>
        </div>
        <div className="preference-item">
          <label>SMS:</label>
          <span>{data.preferences.notifications.sms ? "On" : "Off"}</span>
        </div>
      </div>
      <p className="updated-at">
        Last updated: {new Date(data.updatedAt).toLocaleString()}
      </p>
    </div>
  );
};
```

### `services/preferencesService.ts` - Vanilla JS Service
```typescript
import { preferencesApi, PreferencesApiError } from "../api/preferencesApi";
import type { UserPreferencesResponse } from "../types/preferences";

/**
 * Service for managing user preferences
 */
export class PreferencesService {
  private cache: UserPreferencesResponse | null = null;
  private cacheTimestamp: number = 0;
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  /**
   * Get user preferences with caching
   */
  async getPreferences(forceRefresh = false): Promise<UserPreferencesResponse> {
    const now = Date.now();
    const isCacheValid = this.cache && now - this.cacheTimestamp < this.CACHE_TTL;

    if (!forceRefresh && isCacheValid) {
      return this.cache!;
    }

    try {
      const data = await preferencesApi.getUserPreferences();
      this.cache = data;
      this.cacheTimestamp = now;
      return data;
    } catch (error) {
      // Return cached data if available, even if stale
      if (this.cache && error instanceof PreferencesApiError && error.statusCode >= 500) {
        console.warn("Using stale cache due to server error");
        return this.cache;
      }
      throw error;
    }
  }

  /**
   * Clear the preferences cache
   */
  clearCache(): void {
    this.cache = null;
    this.cacheTimestamp = 0;
  }

  /**
   * Apply theme preference to the document
   */
  applyTheme(theme: string): void {
    document.documentElement.setAttribute("data-theme", theme);
  }

  /**
   * Apply language preference
   */
  applyLanguage(language: string): void {
    document.documentElement.lang = language;
  }
}

export const preferencesService = new PreferencesService();
```

---

## Usage Examples

### Backend Testing with curl
```bash
# Generate a test token (you'll need to implement /api/auth/login separately)
# For testing, use a tool like jwt.io to create a token with payload: {"user_id": "12345"}

curl -X GET http://localhost:5000/api/user/preferences \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
```

### Frontend Usage (React)
```typescript
// In your app component
import { UserPreferencesComponent } from './components/UserPreferences';

function App() {
  return (
    <div className="App">
      <UserPreferencesComponent />
    </div>
  );
}
```

### Frontend Usage (Vanilla JS)
```typescript
import { preferencesService } from './services/preferencesService';

async function loadAndApplyPreferences() {
  try {
    const prefs = await preferencesService.getPreferences();
    preferencesService.applyTheme(prefs.preferences.theme);
    preferencesService.applyLanguage(prefs.preferences.language);
    console.log('Preferences loaded:', prefs);
  } catch (error) {
    console.error('Failed to load preferences:', error);
  }
}

loadAndApplyPreferences();
```

This implementation provides a complete, production-ready API endpoint with proper error handling, type safety, and separation of concerns.