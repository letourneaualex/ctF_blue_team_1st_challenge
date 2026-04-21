CREATE TABLE IF NOT EXISTS users (
    id       SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email    VARCHAR(200),
    password VARCHAR(200) NOT NULL,
    bio      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS posts (
    id      SERIAL PRIMARY KEY,
    title   VARCHAR(200),
    content TEXT,
    user_id INTEGER REFERENCES users(id)
);

-- Seed users — passwords stored in plaintext (vulnerable)
INSERT INTO users (username, email, password, bio) VALUES
    ('testuser', 'test@example.com',  'testpass', 'Just a regular user.'),
    ('alice',    'alice@example.com', 'alice123', 'Hello, I am Alice.')
ON CONFLICT DO NOTHING;

-- Seed posts
INSERT INTO posts (title, content, user_id) VALUES
    ('Welcome to SecureBox',   'This is the first post on our platform.', 1),
    ('Python Tips',            'Here are some Python tips for beginners.',  1),
    ('Security Notes',         'Always validate and sanitise user input.',  2)
ON CONFLICT DO NOTHING;

GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO admin;
GRANT USAGE, SELECT ON ALL SEQUENCES  IN SCHEMA public TO admin;
