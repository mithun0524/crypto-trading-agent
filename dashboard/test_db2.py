import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env.local')
url = os.environ.get('NEXT_PUBLIC_SUPABASE_URL')
key = os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY')
if not url or not key:
    print('Missing supabase url or key in .env.local')
    sys.exit(1)

supabase = create_client(url, key)
res = supabase.table('crypto_live_quotes').select('*').execute()
print(res.data)
