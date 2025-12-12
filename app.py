from flask import Flask, request, jsonify
from models import organizations_col, admins_col, org_collection_name, ensure_org_collection, drop_org_collection, master_db
from utils import hash_password, check_password, create_jwt, decode_jwt
from config import FLASK_SECRET_KEY

app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY

# -------------------------
# Helpers & decorators
# -------------------------

def auth_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth:
            return jsonify({'error': 'Authorization header missing'}), 401
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Invalid authorization header'}), 401
        token = auth.split(' ', 1)[1]
        try:
            payload = decode_jwt(token)
        except Exception:
            return jsonify({'error': 'Invalid or expired token'}), 401
        request.user = payload
        return fn(*args, **kwargs)
    return wrapper

# -------------------------
# Endpoint: Create Organization
# POST /org/create
# -------------------------
@app.route('/org/create', methods=['POST'])
def create_org():
    data = request.get_json() or {}
    org_name = data.get('organization_name')
    email = data.get('email')
    password = data.get('password')

    if not org_name or not email or not password:
        return jsonify({'error': 'organization_name, email and password are required'}), 400

    # Check org exists
    existing = organizations_col.find_one({'organization_name': {'$regex': f'^{org_name}$', '$options': 'i'}})
    if existing:
        return jsonify({'error': 'Organization name already exists'}), 400

    # create per-org collection
    cname = org_collection_name(org_name)
    ensure_org_collection(org_name)

    # create admin user in admins_col
    hashed = hash_password(password)  # stored as UTF-8 string
    admin_doc = {
        'email': email.lower(),
        'password': hashed,
        'organization': org_name,
        'created_at': None
    }
    admin_id = admins_col.insert_one(admin_doc).inserted_id

    # store organization in master DB
    org_doc = {
        'organization_name': org_name,
        'collection_name': cname,
        'connection': {
            'db': master_db.name
        },
        'admin_ref': admin_id,
        'created_at': None
    }
    org_id = organizations_col.insert_one(org_doc).inserted_id

    # return basic metadata
    return jsonify({
        'message': 'Organization created',
        'organization': {
            'id': str(org_id),
            'organization_name': org_name,
            'collection_name': cname,
            'admin_id': str(admin_id)
        }
    }), 201

# -------------------------
# Endpoint: Get Organization by Name
# GET /org/get?organization_name=...
# -------------------------
@app.route('/org/get', methods=['GET'])
def get_org():
    org_name = request.args.get('organization_name')
    if not org_name:
        return jsonify({'error': 'organization_name is required as query param'}), 400

    org = organizations_col.find_one({'organization_name': {'$regex': f'^{org_name}$', '$options': 'i'}})
    if not org:
        return jsonify({'error': 'Organization not found'}), 404

    # prepare response
    org['_id'] = str(org['_id'])
    org['admin_ref'] = str(org['admin_ref'])
    return jsonify({'organization': org}), 200

# -------------------------
# Endpoint: Update Organization
# PUT /org/update
# -------------------------
@app.route('/org/update', methods=['PUT'])
def update_org():
    data = request.get_json() or {}
    org_name = data.get('organization_name')  # current name
    new_org_name = data.get('new_organization_name') or data.get('organization_name_new')
    email = data.get('email')
    password = data.get('password')

    if not org_name or not new_org_name:
        return jsonify({'error': 'organization_name and new_organization_name are required'}), 400

    org = organizations_col.find_one({'organization_name': {'$regex': f'^{org_name}$', '$options': 'i'}})
    if not org:
        return jsonify({'error': 'Organization not found'}), 404

    # check new name not taken (case-insensitive)
    already = organizations_col.find_one({'organization_name': {'$regex': f'^{new_org_name}$', '$options': 'i'}})
    if already and str(already['_id']) != str(org['_id']):
        return jsonify({'error': 'New organization name already exists'}), 400

    # create new collection for new org name
    new_cname = org_collection_name(new_org_name)
    ensure_org_collection(new_org_name)

    # copy data from old collection to new
    old_cname = org['collection_name']
    if old_cname == new_cname:
        # nothing to copy
        pass
    else:
        # copy documents
        old_col = master_db[old_cname]
        new_col = master_db[new_cname]
        docs = list(old_col.find({}))
        if docs:
            for d in docs:
                d.pop('_id', None)
            new_col.insert_many(docs)

        # optionally drop old collection (commented out; keep until sure)
        # master_db.drop_collection(old_cname)

    # update admin reference if email/password provided
    if email and password:
        # find admin and update
        admin = admins_col.find_one({'_id': org['admin_ref']})
        if admin:
            hashed = hash_password(password)
            admins_col.update_one({'_id': org['admin_ref']}, {'$set': {'email': email.lower(), 'password': hashed}})

    # update organization doc
    organizations_col.update_one({'_id': org['_id']}, {'$set': {'organization_name': new_org_name, 'collection_name': new_cname}})

    updated = organizations_col.find_one({'_id': org['_id']})
    updated['_id'] = str(updated['_id'])
    updated['admin_ref'] = str(updated['admin_ref'])

    return jsonify({'message': 'Organization updated', 'organization': updated}), 200

# -------------------------
# Endpoint: Delete Organization
# DELETE /org/delete
# Body: { organization_name }
# Requires JWT admin auth and admin must belong to that organization
# -------------------------
@app.route('/org/delete', methods=['DELETE'])
@auth_required
def delete_org():
    data = request.get_json() or {}
    org_name = data.get('organization_name')
    if not org_name:
        return jsonify({'error': 'organization_name required'}), 400

    # find org
    org = organizations_col.find_one({'organization_name': {'$regex': f'^{org_name}$', '$options': 'i'}})
    if not org:
        return jsonify({'error': 'Organization not found'}), 404

    # ensure requester is admin and belongs to this org
    user = request.user
    if 'admin_id' not in user or 'organization' not in user:
        return jsonify({'error': 'Invalid token payload'}), 401
    if user['organization'].lower() != org['organization_name'].lower():
        return jsonify({'error': 'Unauthorized: not an admin of this organization'}), 403

    # drop per-org collection
    dropped = drop_org_collection(org['organization_name'])

    # remove admin
    admins_col.delete_one({'_id': org['admin_ref']})

    # remove org record
    organizations_col.delete_one({'_id': org['_id']})

    return jsonify({'message': 'Organization deleted', 'dropped_collection': dropped}), 200

# -------------------------
# Endpoint: Admin Login
# POST /admin/login
# Body: { email, password }
# -------------------------
@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    email = (data.get('email') or '').lower()
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'email and password required'}), 400

    admin = admins_col.find_one({'email': email})
    if not admin:
        return jsonify({'error': 'Invalid credentials'}), 401

    # convert stored password to bytes/verify
    stored_hash = admin.get('password')
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode('utf-8')
    try:
        stored_hash = bytes(stored_hash)
    except Exception:
        pass

    if not check_password(password, stored_hash):
        return jsonify({'error': 'Invalid credentials'}), 401

    # find associated org
    org = organizations_col.find_one({'admin_ref': admin['_id']})
    org_id = str(org['_id']) if org else None

    payload = {
        'admin_id': str(admin['_id']),
        'organization': org['organization_name'] if org else None
    }

    token = create_jwt(payload)

    return jsonify({'token': token, 'organization_id': org_id}), 200

# -------------------------
# Basic root
# -------------------------
@app.route('/')
def index():
    return jsonify({'message': 'Multitenant Organization Service (Flask)'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


