# TaskFlow Kubernetes Deployment

This project deploys the TaskFlow application on Kubernetes.

The application consists of:

- Frontend application
- Backend API
- PostgreSQL database
- Redis service

---

# Architecture

```
Browser
  |-- Frontend: http://54.226.139.213:30400
  |     NodePort -> taskflow-frontend Pod
  |
  +-- API: http://54.226.139.213:30500/api/...
        NodePort -> taskflow-api Pod
                      |-- PostgreSQL Service -> PostgreSQL Pod -> PVC
                      +-- Redis Service -> Redis Pod
```

---

# Kubernetes Resources

| Resource | Purpose |
|---|---|
| Namespace | Isolates TaskFlow resources |
| Deployment | Manages application Pods |
| Service | Provides stable networking |
| ConfigMap | Stores non-sensitive configuration |
| Secret | Stores sensitive information |
| PersistentVolumeClaim | Provides persistent storage for PostgreSQL |
| PostgreSQL | Application database |
| Redis | Cache / queue storage |

---

# Namespace

The application runs inside:

```
taskflow
```

Create namespace:

```bash
kubectl apply -f 00-namespace.yaml
```

View namespaces:

```bash
kubectl get namespaces
```

---

# Deploy Application

Run these commands from the project root on the server (the directory containing `00-namespace.yaml` and this README).

Apply each manifest in order. You can copy and paste this entire block:

```bash
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-backend-configmap.yaml
kubectl apply -f 02-backend-secret.yaml
kubectl apply -f 03-postgres-storage.yaml
kubectl apply -f 03-postgres.yaml
kubectl apply -f 04-postgres-service.yaml
kubectl apply -f 05-redis.yaml
kubectl apply -f 06-redis-service.yaml
kubectl apply -f 07-backend.yaml
kubectl apply -f 08-backend-service.yaml
kubectl apply -f 09-frontend-config.yaml
kubectl apply -f 10-frontend.yaml
kubectl apply -f 11-frontend-service.yaml
```

Alternatively, apply all Kubernetes manifests in the current directory:

```bash
kubectl apply -f .
```

To reapply just the PostgreSQL deployment:

```bash
kubectl apply -f 03-postgres.yaml
```

---

# View Resources

## View all resources

```bash
kubectl get all -n taskflow
```

---

## View Pods

List Pods:

```bash
kubectl get pods -n taskflow
```

Detailed information:

```bash
kubectl get pods -n taskflow -o wide
```

Watch Pods:

```bash
kubectl get pods -n taskflow -w
```

---

# Pod Troubleshooting

## Describe Pod

Shows:

- Container status
- Events
- Environment variables
- Volumes
- Errors


```bash
kubectl describe pod <pod-name> -n taskflow
```

Example:

```bash
kubectl describe pod taskflow-api-xxxxx -n taskflow
```

---

## View Logs

View logs:

```bash
kubectl logs <pod-name> -n taskflow
```

Follow logs:

```bash
kubectl logs -f <pod-name> -n taskflow
```

Previous crashed container logs:

```bash
kubectl logs <pod-name> -n taskflow --previous
```

---

# Deployment Commands

## View Deployments

```bash
kubectl get deployments -n taskflow
```

---

## Describe Deployment

```bash
kubectl describe deployment <deployment-name> -n taskflow
```

Example:

```bash
kubectl describe deployment taskflow-api -n taskflow
```

---

## Check Rollout Status

```bash
kubectl rollout status deployment/<deployment-name> -n taskflow
```

Example:

```bash
kubectl rollout status deployment/taskflow-api -n taskflow
```

---

## Restart Deployment

```bash
kubectl rollout restart deployment/<deployment-name> -n taskflow
```

Example:

```bash
kubectl rollout restart deployment/taskflow-api -n taskflow
```

---

## View Rollout History

```bash
kubectl rollout history deployment/<deployment-name> -n taskflow
```

---

# Service Commands

## List Services

```bash
kubectl get svc -n taskflow
```

---

## Describe Service

Shows:

- Cluster IP
- Ports
- Selectors
- Endpoints


```bash
kubectl describe svc <service-name> -n taskflow
```

Example:

```bash
kubectl describe svc postgres -n taskflow
```

---

## View Service Endpoints

```bash
kubectl get endpoints -n taskflow
```

Example:

```
postgres service
        |
        |
postgres pod IP
```

---

# ConfigMap Commands

ConfigMaps store non-sensitive application configuration.

Example:

```
DB_HOST=postgres
DB_PORT=5432
REDIS_HOST=redis
```

---

## List ConfigMaps

```bash
kubectl get configmap -n taskflow
```

---

## View ConfigMap

```bash
kubectl describe configmap <configmap-name> -n taskflow
```

Example:

```bash
kubectl describe configmap taskflow-backend-config -n taskflow
```

---

## View ConfigMap YAML

```bash
kubectl get configmap <configmap-name> -n taskflow -o yaml
```

---

# Secret Commands

Secrets store sensitive information.

Example:

```
DB_PASSWORD
API_KEYS
TOKENS
```

---

## List Secrets

```bash
kubectl get secrets -n taskflow
```

---

## Describe Secret

```bash
kubectl describe secret <secret-name> -n taskflow
```

---

## View Secret YAML

```bash
kubectl get secret <secret-name> -n taskflow -o yaml
```

---

## Decode Secret Value

Kubernetes stores secrets as base64 encoded values.

Decode:

```bash
echo <encoded-value> | base64 -d
```

---

# Persistent Storage

PostgreSQL requires persistent storage because database data must survive Pod restarts.

Without storage:

```
PostgreSQL Pod

      |
      |

Container filesystem

      |
      |

Pod deleted

      |
      |

Database data lost
```

With Persistent Storage:

```
PostgreSQL Pod

      |
      |

PersistentVolumeClaim

      |
      |

PersistentVolume

      |
      |

Disk Storage
```

---

# PostgreSQL Storage

Create PostgreSQL storage:

```bash
kubectl apply -f 03-postgres-storage.yaml
```

---

## View PersistentVolumeClaims

```bash
kubectl get pvc -n taskflow
```

Expected:

```
NAME             STATUS
postgres-pvc     Bound
```

---

## Describe PVC

```bash
kubectl describe pvc postgres-pvc -n taskflow
```

---

## View PersistentVolumes

```bash
kubectl get pv
```

---

# Redis Storage Decision

Redis does not use persistent storage in this deployment.

Reason:

- Redis is treated as temporary data storage.
- PostgreSQL is the source of truth.
- Redis data can be recreated after restart.

Architecture:

```
Backend API

    |
    |

 Redis
(Cache / Temporary Data)

    |
    |

 PostgreSQL
(Permanent Data)
```

---

# Access Containers

## Enter Container Shell

Using bash:

```bash
kubectl exec -it <pod-name> -n taskflow -- bash
```

Using sh:

```bash
kubectl exec -it <pod-name> -n taskflow -- sh
```

---

## Run Command Inside Container

Example:

```bash
kubectl exec <pod-name> -n taskflow -- ls
```

---

# Environment Variables

View environment variables:

```bash
kubectl exec -it <pod-name> -n taskflow -- env
```

Filter:

```bash
kubectl exec -it <pod-name> -n taskflow -- env | grep DB
```

---

# PostgreSQL Commands

Enter PostgreSQL:

```bash
kubectl exec -it <postgres-pod> -n taskflow -- psql -U taskflow -d taskflow
```

Inside PostgreSQL:

List databases:

```sql
\l
```

List tables:

```sql
\dt
```

Query data:

```sql
CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY,title VARCHAR(255) NOT NULL,description TEXT,status VARCHAR(30) DEFAULT 'TODO',priority VARCHAR(20) DEFAULT 'MEDIUM',created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
INSERT INTO tasks(title,description,status,priority) SELECT * FROM (VALUES ('Deploy TaskFlow API','Deploy backend application to Kubernetes','IN_PROGRESS','HIGH'),('Configure monitoring','Install Prometheus and Grafana','TODO','MEDIUM'),('Configure persistent storage','Create PVC for PostgreSQL','COMPLETED','HIGH')) AS v(title,description,status,priority) WHERE NOT EXISTS (SELECT 1 FROM tasks);
```

Exit:

```sql
\q
```

---

# Redis Commands

Enter Redis:

```bash
kubectl exec -it <redis-pod> -n taskflow -- redis-cli
```

Test Redis:

```bash
PING
```

Expected:

```
PONG
```

View keys:

```bash
KEYS *
```

---

# Kubernetes Events

View events:

```bash
kubectl get events -n taskflow
```

Sort by time:

```bash
kubectl get events -n taskflow --sort-by=.metadata.creationTimestamp
```

---

# Troubleshooting Guide

## Public Backend Access (NodePort)

The frontend is exposed on port `30400` and the backend on port `30500`.
The browser should call `http://54.226.139.213:30500/api/status` and
`http://54.226.139.213:30500/api/tasks` directly.

`08-backend-service.yaml` exposes the backend using NodePort `30500`.
`09-frontend-config.yaml` sets `API_URL` to `http://54.226.139.213:30500`.
`10-frontend.yaml` passes this setting to the frontend container without a custom Nginx configuration mount.

After copying these files to the server, run from the project root:

```bash
kubectl apply -f 08-backend-service.yaml
kubectl apply -f 09-frontend-config.yaml
kubectl apply -f 10-frontend.yaml
kubectl rollout restart deployment/taskflow-frontend -n taskflow
kubectl rollout status deployment/taskflow-frontend -n taskflow
curl -i http://54.226.139.213:30500/api/status
curl -i http://54.226.139.213:30500/api/tasks
```

Allow inbound TCP port `30500` in the server's security group/firewall for the clients using the app. Keep port `30400` accessible for the frontend.

**Frontend integration still needs verification:** a container environment variable only changes browser requests if the frontend image supports that setting. If browser requests still go to port `30400`, update the frontend source to use the public backend URL and rebuild its image. This repository contains deployment manifests, not the frontend source. Do not add `/api` twice when constructing request URLs.

Requests between these two ports are cross-origin; the backend must allow the frontend origin `http://54.226.139.213:30400` through CORS. Update the public IP in the configuration if the server address changes.

---

## Pod is Pending

Check:

```bash
kubectl describe pod <pod-name> -n taskflow
```

Check:

```
Events:
```

Common causes:

- Insufficient resources
- Storage problems
- Scheduling issues

---

## Pod is CrashLoopBackOff

Check logs:

```bash
kubectl logs <pod-name> -n taskflow
```

Previous crash:

```bash
kubectl logs <pod-name> -n taskflow --previous
```

---

## Backend Cannot Connect To Database

Check backend environment:

```bash
kubectl exec -it <backend-pod> -n taskflow -- env | grep DB
```

Expected:

```
DB_HOST=postgres
DB_PORT=5432
DB_NAME=taskflow
```

Check PostgreSQL service:

```bash
kubectl get svc postgres -n taskflow
```

Check endpoints:

```bash
kubectl get endpoints postgres -n taskflow
```

---

# Port Forwarding

Access backend locally:

```bash
kubectl port-forward svc/taskflow-api 5000:5000 -n taskflow
```

Access frontend locally:

```bash
kubectl port-forward svc/taskflow-frontend 8080:80 -n taskflow
```

---

# Delete Resources

Delete deployed resources:

```bash
kubectl delete -f .
```

Delete namespace:

```bash
kubectl delete namespace taskflow
```

---

# Useful Commands

Current Kubernetes context:

```bash
kubectl config current-context
```

View all Pods:

```bash
kubectl get pods -A
```

View all resources:

```bash
kubectl get all -A
```

Watch Pods:

```bash
watch kubectl get pods -n taskflow
```

---

# Docker Images

Backend:

```
incriszz/taskflow-api
```

Frontend:

```
incriszz/taskflow-frontend
```

---

# Debugging Flow

When something breaks:

## 1. Check Pod status

```bash
kubectl get pods -n taskflow
```

## 2. Describe failing Pod

```bash
kubectl describe pod <pod-name> -n taskflow
```

## 3. Check logs

```bash
kubectl logs <pod-name> -n taskflow
```

## 4. Check Services

```bash
kubectl get svc -n taskflow
```

## 5. Check Endpoints

```bash
kubectl get endpoints -n taskflow
```

## 6. Enter Container

```bash
kubectl exec -it <pod-name> -n taskflow -- sh
```

---

# Notes

- PostgreSQL uses PersistentVolumeClaim to preserve database data.
- Redis does not use persistent storage because it is not the source of truth.
- PostgreSQL and Redis communicate internally using Kubernetes Service DNS.
- Backend connects to PostgreSQL using:

```
DB_HOST=postgres
```

- Backend connects to Redis using:

```
REDIS_HOST=redis
```

Kubernetes automatically resolves these service names inside the cluster.
