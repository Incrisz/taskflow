import { createClient } from 'redis';
export const redis = createClient({url:`redis://${process.env.REDIS_HOST||'localhost'}:${process.env.REDIS_PORT||6379}`});
redis.on('error', err => console.error('Redis error:', err.message));
export async function connectRedis(){ if(!redis.isOpen) await redis.connect(); }
export async function redisHealthy(){ try { if(!redis.isOpen) await connectRedis(); return (await redis.ping())==='PONG'; } catch { return false; } }
