-- =============================================
-- RBAC Initial Inserts:
-- =============================================

-- 1 Users
INSERT OR IGNORE INTO user (username, password_hash, email, enabled) VALUES
('admin', 'hashed_password_admin', '', 1),
('red', 'hashed_password_red', '', 1),
('guest', 'hashed_password_fred', '', 1);

-- 2. Roles
INSERT OR IGNORE INTO role (role_name) VALUES
('admin'),
('standard');

-- 3. Role permissions using wildcards

-- Admin role: full access to all blueprints
INSERT OR IGNORE INTO role_permission (role_name, blueprint, view) VALUES
('admin', 'admin', '*'),
('admin', 'personal', '*'),
('admin', 'parkrun', '*'),
('admin', 'analytics', '*');

-- Standard role: access to all blueprints except admin
INSERT OR IGNORE INTO role_permission (role_name, blueprint, view) VALUES
('standard', 'personal', '*'),
('standard', 'parkrun', '*'),
('standard', 'analytics', '*');

-- 4. User roles
INSERT OR IGNORE INTO user_role (username, role_name) VALUES
('admin', 'admin'),
('red', 'standard'),
('fred', 'standard');

-- 5. User overrides for Fred
-- guest  can only access parkrun: deny personal and analytics
INSERT OR IGNORE INTO user_override (username, blueprint, view, effect) VALUES
('guest', 'personal', '*', 'deny'),
('guest', 'analytics', '*', 'deny');
