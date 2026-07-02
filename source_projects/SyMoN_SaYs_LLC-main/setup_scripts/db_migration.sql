ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    sender_username TEXT NOT NULL REFERENCES user_profiles(username) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE chat_messages TO symoneural_user;
GRANT USAGE, SELECT ON SEQUENCE chat_messages_id_seq TO symoneural_user;
