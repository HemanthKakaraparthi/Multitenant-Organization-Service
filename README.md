# Multitenant-Organization-Service
A lightweight Flask-based multitenant service with MongoDB, supporting organization creation, admin authentication, and per-tenant isolated collections.

**🚀 Requirements**

Python 3.9+

MongoDB (local or remote instance)

**📦 Installation**

1.Clone the repository

git clone <repo-url>
cd <project-folder>


2.Create and activate a virtual environment

python -m venv venv
source venv/bin/activate        # macOS / Linux
# OR
venv\Scripts\activate           # Windows


3.Install dependencies

pip install -r requirements.txt

**🛠️ API Endpoints**
### Organization Endpoints
▶️ Create Organization

POST /org/create
Body:

{
  "organization_name": "example_org",
  "email": "admin@example.com",
  "password": "your_password"
}

🔍 Get Organization

GET /org/get?organization_name=<name>

Example:

/org/get?organization_name=example_org

✏️ Update Organization

PUT /org/update
Body:

{
  "organization_name": "old_name",
  "new_organization_name": "new_name",
  "email": "optional_updated_email",
  "password": "optional_updated_password"
}

🗑️ Delete Organization

DELETE /org/delete
Headers:

Authorization: Bearer <token>


Body:

{
  "organization_name": "example_org"
}

**🧑‍💼 Admin Authentication**
🔐 Admin Login

POST /admin/login
Body:

{
  "email": "admin@example.com",
  "password": "your_password"
}


Returns: JWT token containing admin_id and organization.

**🔒 Security Notes**

Passwords are hashed using bcrypt before storage.

JWT tokens are signed using JWT_SECRET and include:

admin_id

organization

**🏗️ Multitenancy Architecture**

Each organization gets its own MongoDB collections, created dynamically.

Naming convention:

org_<organization_name>_collectionName


All tenant collections exist inside the same master MongoDB database.
