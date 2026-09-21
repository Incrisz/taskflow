import { NextFunction,Request,Response } from 'express'; import client from 'prom-client';
client.collectDefaultMetrics();
export const requestCounter=new client.Counter({name:'taskflow_http_requests_total',help:'Total HTTP requests',labelNames:['method','route','status']});
export const requestDuration=new client.Histogram({name:'taskflow_http_request_duration_seconds',help:'HTTP request duration',labelNames:['method','route','status']});
export function metricsMiddleware(req:Request,res:Response,next:NextFunction){ const end=requestDuration.startTimer(); res.on('finish',()=>{const labels={method:req.method,route:req.route?.path||req.path,status:String(res.statusCode)};requestCounter.inc(labels);end(labels)});next(); }
export { client };
