import secrets
import mysql.connector

def generate_api_key():
    return secrets.token_hex(32) 

def save_api_key_to_db(user_id, api_key):
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="Kyaw550550#",
        database="plagiarism_checker"
    )
    cursor = conn.cursor()
    
    sql = "INSERT INTO api_keys (user_id, api_key) VALUES (%s, %s)"
    val = (user_id, api_key) 
    cursor.execute(sql, val)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"API key for user {user_id} saved.")

# Step 3: Get the correct user_id (assumed to be an integer)
# You can replace this with an actual user ID from your 'users' table.
user_id = 2  # Replace with the actual user ID (must be an integer)
new_api_key = generate_api_key()  
save_api_key_to_db(user_id, new_api_key)

print(f"Generated API Key: {new_api_key}")
