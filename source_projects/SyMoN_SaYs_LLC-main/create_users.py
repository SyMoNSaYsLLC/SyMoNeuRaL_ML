
import psycopg
from werkzeug.security import generate_password_hash

# Database connection details
DB_URL = "postgresql://symoneural_user:symon_says_secure_password@localhost/symoneural_db"

# User data
users = [
    {'username': 'symoneural', 'password': 'ilovesymon', 'full_name': 'Symoneural Admin'},
    {'username': 'garrett', 'password': 'iloveraven', 'full_name': 'Garrett'},
    {'username': 'raven', 'password': 'ilovegarrett', 'full_name': 'Raven'},
    {'username': 'ben', 'password': 'ilovegarrett', 'full_name': 'Ben'}
]

def create_users():
    try:
        with psycopg.connect(DB_URL) as connection:
            with connection.cursor() as cursor:
                for user in users:
                    password_hash = generate_password_hash(user['password'])
                    cursor.execute(
                        """
                        INSERT INTO user_profiles (username, full_name, password_hash, photo_path, bio, country, date_of_birth)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (username) DO NOTHING;
                        """,
                        (user['username'], user['full_name'], password_hash, f"avatars/{user['username']}.png", f"Bio for {user['full_name']}", 'US', '2000-01-01')
                    )
                print("Users created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_users()
