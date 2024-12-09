from aiohttp import ClientSession

from keys import AIRTABLE_API_KEY, AIRTABLE_BASE_ID

async def ensure_table_exists(table_name, fields):
    """Ensure that a table exists in Airtable; if not, create it."""
    async with ClientSession() as session:
        url = f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables"
        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }
        async with session.get(url, headers=headers) as response:
            existing_tables = await response.json()
            table_names = [table['name'] for table in existing_tables['tables']]
        
        if table_name not in table_names:
            async with session.post(url, headers=headers, json={
                "name": table_name,
                "fields": fields
            }) as response:
                if response.status == 200:
                    print(f"Table '{table_name}' created successfully.")
                else:
                    print(f"Failed to create table '{table_name}': {await response.text()}")