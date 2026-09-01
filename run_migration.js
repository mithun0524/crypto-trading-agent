const { Client } = require('pg');
const fs = require('fs');

async function main() {
  const sql = fs.readFileSync('supabase/migrations/001_init.sql', 'utf8');
  
  const client = new Client({
    connectionString: 'postgresql://postgres:Mithun%4024feb@db.ojojutcclxvdlrjdicmv.supabase.co:5432/postgres'
  });

  await client.connect();
  console.log('Connected to Supabase PostgreSQL!');

  try {
    await client.query(sql);
    console.log('Migration successfully applied!');
  } catch (err) {
    console.error('Error applying migration:', err);
  } finally {
    await client.end();
  }
}

main();
