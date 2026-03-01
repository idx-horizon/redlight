-- =============================================
-- RBAC Schema
-- =============================================

-- Users table
CREATE TABLE IF NOT EXISTS user (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    email TEXT,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1))
);

-- Roles table
CREATE TABLE IF NOT EXISTS role (
    role_name TEXT PRIMARY KEY
);

-- Role permissions table (use role_name as FK)
CREATE TABLE IF NOT EXISTS role_permission (
    role_name TEXT NOT NULL,
    blueprint TEXT NOT NULL,
    view TEXT NOT NULL,
    PRIMARY KEY (role_name, blueprint, view),
    FOREIGN KEY (role_name) REFERENCES role(role_name) ON DELETE CASCADE
);

-- User roles table (many-to-many)
CREATE TABLE IF NOT EXISTS user_role (
    username TEXT NOT NULL,
    role_name TEXT NOT NULL,
    PRIMARY KEY (username, role_name),
    FOREIGN KEY (username) REFERENCES user(username) ON DELETE CASCADE,
    FOREIGN KEY (role_name) REFERENCES role(role_name) ON DELETE CASCADE
);

-- User overrides (allow / deny per blueprint/view)
CREATE TABLE IF NOT EXISTS user_override (
    username TEXT NOT NULL,
    blueprint TEXT NOT NULL,
    view TEXT NOT NULL,
    effect TEXT NOT NULL CHECK(effect IN ('allow','deny')),
    PRIMARY KEY (username, blueprint, view),
    FOREIGN KEY (username) REFERENCES user(username) ON DELETE CASCADE
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_role_username ON user_role(username);
CREATE INDEX IF NOT EXISTS idx_role_permission_role_name ON role_permission(role_name);
CREATE INDEX IF NOT EXISTS idx_user_override_username ON user_override(username);
CREATE INDEX IF NOT EXISTS idx_role_permission_blueprint ON role_permission(blueprint);
CREATE INDEX IF NOT EXISTS idx_user_override_blueprint ON user_override(blueprint);
