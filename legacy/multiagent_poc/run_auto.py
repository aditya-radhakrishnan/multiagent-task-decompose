#!/usr/bin/env python3
"""
Run automatic task decomposition experiment
"""

from auto_orchestrator import AutoDecomposingOrchestrator

def run_simple_task():
    """Test with the original simple task"""
    orchestrator = AutoDecomposingOrchestrator(clean_start=True)
    
    task = """
Design and implement a new API endpoint: GET /api/user/preferences

Requirements:
- Return user preference settings (theme, language, timezone, notifications)
- Requires authentication
- Handle error cases appropriately
- Provide both backend (Python/Flask) and frontend (TypeScript) implementations
"""
    
    print("="*60)
    print("TEST 1: Simple Task (for comparison)")
    print("="*60)
    
    orchestrator.run(task, max_iterations=5)
    

def run_complex_task():
    """Test with a complex task that should benefit from decomposition"""
    orchestrator = AutoDecomposingOrchestrator(clean_start=True)
    
    task = """
Build a complete user authentication system with the following requirements:
- User registration with email verification
- Login with JWT tokens  
- Password reset functionality
- Role-based access control (admin, user, guest)
- Rate limiting on authentication endpoints
- Audit logging of authentication events
- Both backend (Python/Flask) and frontend (React/TypeScript) implementations
"""
    
    print("="*60)
    print("TEST 2: Complex Task (should spawn more agents)")
    print("="*60)
    
    orchestrator.run(task, max_iterations=8)


def run_payment_task():
    """Test with payment integration system"""
    orchestrator = AutoDecomposingOrchestrator(clean_start=True)
    
    task = """
Build a payment processing system:
- Stripe payment integration for checkout
- Subscription management (monthly/annual plans)
- Payment history and receipts
- Webhook handling for payment events
- Admin dashboard for viewing transactions
- Refund processing
- Backend (Python/Flask) and frontend checkout flow (React/TypeScript)
"""
    
    print("="*60)
    print("TEST 4: Payment Integration")
    print("="*60)
    
    orchestrator.run(task, max_iterations=10)


def run_analytics_task():
    """Test with analytics dashboard system"""
    orchestrator = AutoDecomposingOrchestrator(clean_start=True)
    
    task = """
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
    
    print("="*60)
    print("TEST 5: Analytics Dashboard")
    print("="*60)
    
    orchestrator.run(task, max_iterations=10)


def run_ecommerce_task():
    """Test with e-commerce catalog system (very complex)"""
    orchestrator = AutoDecomposingOrchestrator(clean_start=True)
    
    task = """
Build a product catalog system with:
- Database schema for products, categories, and inventory
- Search functionality with filters (price range, category, rating)
- Product recommendation engine based on viewing history
- Admin dashboard for product management (CRUD operations)
- Public-facing product listing and detail pages
- Shopping cart integration
- Image upload and storage management
- Backend (Python/Flask), Frontend (React/TypeScript), Database (PostgreSQL)
"""
    
    print("="*60)
    print("TEST 3: E-commerce Catalog (should spawn 3-4 agents)")
    print("="*60)
    
    orchestrator.run(task, max_iterations=10)


def run_custom_task():
    """Run with user-provided task"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        AUTOMATIC TASK DECOMPOSITION EXPERIMENT           ║
╚══════════════════════════════════════════════════════════╝

The system will:
1. Analyze your task description
2. Automatically break it into subtasks
3. Determine dependencies
4. Spawn and coordinate agents dynamically
""")
    
    print("\nEnter your task description (press Enter twice when done):")
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    
    task = "\n".join(lines[:-1])  # Remove the last empty line
    
    if not task.strip():
        print("No task provided. Exiting.")
        return
    
    orchestrator = AutoDecomposingOrchestrator(clean_start=True)
    orchestrator.run(task, max_iterations=8)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "simple":
            run_simple_task()
        elif mode == "complex":
            run_complex_task()
        elif mode == "ecommerce":
            run_ecommerce_task()
        elif mode == "payment":
            run_payment_task()
        elif mode == "analytics":
            run_analytics_task()
        elif mode == "custom":
            run_custom_task()
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python run_auto.py [simple|complex|ecommerce|payment|analytics|custom]")
    else:
        print("Usage: python run_auto.py [simple|complex|ecommerce|payment|analytics|custom]")
        print("\nModes:")
        print("  simple    - Run with simple API endpoint task")
        print("  complex   - Run with complex auth system task")
        print("  ecommerce - Run with e-commerce catalog system task")
        print("  payment   - Run with payment integration task")
        print("  analytics - Run with analytics dashboard task")
        print("  custom    - Enter your own task")
