"""
Generate varied tasks for statistical validation of auto-decomposition
"""

SIMPLE_TASKS = [
    {
        "id": "simple_1",
        "name": "Todo List API",
        "description": """
Build a REST API for a todo list application:
- CRUD operations for todos (create, read, update, delete)
- Each todo has: title, description, status (pending/completed), due date
- Filter todos by status
- Backend (Python/Flask) and simple frontend (HTML/JavaScript)
"""
    },
    {
        "id": "simple_2", 
        "name": "Weather Dashboard",
        "description": """
Build a weather dashboard application:
- Fetch weather data from an external API
- Display current weather for a searched city
- Show 5-day forecast
- Save favorite cities
- Backend (Python/Flask) and frontend (React/TypeScript)
"""
    },
    {
        "id": "simple_3",
        "name": "Contact Form API",
        "description": """
Build a contact form system:
- API endpoint to receive contact submissions
- Email notification when form is submitted
- Store submissions in database
- Admin view to see all submissions
- Backend (Python/Flask) and frontend form (React)
"""
    },
    {
        "id": "simple_4",
        "name": "URL Shortener",
        "description": """
Build a URL shortening service:
- Create short URLs from long URLs
- Redirect short URLs to original URLs
- Track click counts for each short URL
- Simple dashboard showing top URLs
- Backend (Python/Flask) and frontend (React/TypeScript)
"""
    },
    {
        "id": "simple_5",
        "name": "Blog Post API",
        "description": """
Build a simple blog API:
- CRUD operations for blog posts (title, content, author, publish date)
- List posts with pagination
- Search posts by title or content
- Like/unlike posts
- Backend (Python/Flask) and frontend reader (React)
"""
    }
]

MEDIUM_TASKS = [
    {
        "id": "medium_1",
        "name": "Authentication System",
        "description": """
Build a complete user authentication system:
- User registration with email verification
- Login with JWT tokens
- Password reset functionality
- Role-based access control (admin, user, guest)
- Rate limiting on authentication endpoints
- Audit logging of authentication events
- Backend (Python/Flask) and frontend (React/TypeScript)
"""
    },
    {
        "id": "medium_2",
        "name": "Payment Integration",
        "description": """
Build a payment processing system:
- Stripe payment integration for checkout
- Subscription management (monthly/annual plans)
- Payment history and receipts
- Webhook handling for payment events
- Admin dashboard for viewing transactions
- Refund processing
- Backend (Python/Flask) and frontend checkout flow (React/TypeScript)
"""
    },
    {
        "id": "medium_3",
        "name": "Notification Service",
        "description": """
Build a multi-channel notification system:
- Send notifications via email, SMS, and push
- User notification preferences management
- Notification templates with variables
- Delivery tracking and status
- Retry logic for failed notifications
- Admin panel for viewing notification logs
- Backend (Python/Flask) and frontend settings UI (React/TypeScript)
"""
    },
    {
        "id": "medium_4",
        "name": "File Upload System",
        "description": """
Build a file management system:
- Upload files with drag-and-drop
- Organize files in folders
- File preview for images and PDFs
- Share files with time-limited links
- Search files by name and tags
- Storage quota management
- Backend (Python/Flask) and frontend file browser (React/TypeScript)
"""
    },
    {
        "id": "medium_5",
        "name": "Booking System",
        "description": """
Build an appointment booking system:
- Calendar view for available time slots
- Book, reschedule, and cancel appointments
- Email confirmations and reminders
- Service provider availability management
- Customer booking history
- Admin dashboard for managing bookings
- Backend (Python/Flask) and frontend booking UI (React/TypeScript)
"""
    }
]

COMPLEX_TASKS = [
    {
        "id": "complex_1",
        "name": "E-commerce Catalog",
        "description": """
Build a product catalog system:
- Database schema for products, categories, and inventory
- Search functionality with filters (price range, category, rating)
- Product recommendation engine based on viewing history
- Admin dashboard for product management (CRUD operations)
- Public-facing product listing and detail pages
- Shopping cart integration
- Image upload and storage management
- Backend (Python/Flask), Frontend (React/TypeScript), Database (PostgreSQL)
"""
    },
    {
        "id": "complex_2",
        "name": "CRM Platform",
        "description": """
Build a customer relationship management system:
- Contact management with custom fields
- Deal pipeline with drag-and-drop stages
- Activity tracking (emails, calls, meetings)
- Task and reminder system
- Reporting dashboard with charts
- Email integration for tracking conversations
- Role-based permissions for team access
- Backend (Python/Flask), Frontend (React/TypeScript), Database (PostgreSQL)
"""
    },
    {
        "id": "complex_3",
        "name": "Analytics Dashboard",
        "description": """
Build a data analytics platform:
- Connect to multiple data sources (CSV, databases, APIs)
- Custom metric definitions and calculations
- Interactive charts and visualizations
- Dashboard builder with drag-and-drop widgets
- Scheduled reports via email
- Data export functionality
- User access control and sharing
- Backend (Python/Flask), Frontend (React/TypeScript), Database (PostgreSQL)
"""
    },
    {
        "id": "complex_4",
        "name": "Social Media Platform",
        "description": """
Build a social networking application:
- User profiles with customizable information
- Post creation (text, images, links)
- Follow/unfollow system and news feed
- Like, comment, and share functionality
- Real-time notifications
- Direct messaging between users
- Content moderation tools
- Backend (Python/Flask), Frontend (React/TypeScript), Database (PostgreSQL)
"""
    },
    {
        "id": "complex_5",
        "name": "Project Management Tool",
        "description": """
Build a project management application:
- Project and task hierarchy
- Kanban board with drag-and-drop
- Gantt chart timeline view
- Time tracking for tasks
- Team member assignment and workload view
- File attachments on tasks
- Comments and activity feed
- Backend (Python/Flask), Frontend (React/TypeScript), Database (PostgreSQL)
"""
    }
]

def get_tasks_by_complexity(complexity: str, n: int = None):
    """Get n tasks of given complexity. If n is None, return all."""
    if complexity == "simple":
        tasks = SIMPLE_TASKS
    elif complexity == "medium":
        tasks = MEDIUM_TASKS
    elif complexity == "complex":
        tasks = COMPLEX_TASKS
    else:
        raise ValueError(f"Unknown complexity: {complexity}")
    
    if n is None:
        return tasks
    return tasks[:n]

def get_all_tasks(n_per_complexity: int = 5):
    """Get n tasks from each complexity tier"""
    return {
        "simple": get_tasks_by_complexity("simple", n_per_complexity),
        "medium": get_tasks_by_complexity("medium", n_per_complexity),
        "complex": get_tasks_by_complexity("complex", n_per_complexity)
    }
