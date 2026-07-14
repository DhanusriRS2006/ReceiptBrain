from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

def test_connection():
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_ANON_KEY")
        
    )
    
    # Test inserting a dummy receipt
    response = supabase.table("receipts").insert({
        "source": "image",
        "raw_text": "TEST - Swiggy Order Total 250"
    }).execute()
    
    print("Connection successful!")
    print("Inserted row:", response.data)
    
    # Clean up test row
    receipt_id = response.data[0]['id']
    supabase.table("receipts").delete().eq("id", receipt_id).execute()
    print("Test row cleaned up. Supabase is ready.")

if __name__ == "__main__":
    test_connection()