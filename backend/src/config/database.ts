import { Pool } from 'pg';
export const pool = new Pool({host:process.env.DB_HOST||'localhost',port:Number(process.env.DB_PORT||5432),database:process.env.DB_NAME||'taskflow',user:process.env.DB_USER||'taskflow',password:process.env.DB_PASSWORD||'taskflow123'});
export async function dbHealthy(){ try { await pool.query('SELECT 1'); return true; } catch { return false; } }
