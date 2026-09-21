# TaskFlow — Docker-Only Deployment Guide

This guide deploys the complete TaskFlow application using **Docker only**.

We will **not use Docker Compose or Kubernetes yet**.

The application consists of:

* TaskFlow Frontend
* TaskFlow API
* PostgreSQL
* Redis

## Architecture

```text
                         User
                          │
                          ▼
                ┌──────────────────┐
                │ TaskFlow Frontend│
                │     Port 3000    │
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │   TaskFlow API   │
                │     Port 5000    │
                └───────┬──────────┘
                        │
                ┌───────┴─────────┐
                │                 │
                ▼                 ▼
         ┌────────────┐      ┌─────────┐
         │ PostgreSQL │      │  Redis  │
         │ Port 5432  │      │Port 6379│
         └──────┬─────┘      └─────────┘
                │
                ▼
          Docker Volume
```

All containers communicate through:

```text
taskflow-network
```

---

# 1. Prerequisites

Verify Docker is installed:

```bash
docker --version
```

Check that Docker is running:

```bash
docker ps
```

---

# 2. Enter the Project Directory

```bash
cd taskflow
```

Check the repository:

```bash
ls
```

You should see directories/files similar to:

```text
backend/
frontend/
database/
kubernetes/
docker-compose.yml
README.md
```

---

# 3. Build the Backend Image

Build the TaskFlow API:

```bash
docker build -t taskflow-api:v1 ./backend
```

Check the image:

```bash
docker images
```

Or:

```bash
docker images | grep taskflow
```

Expected image:

```text
taskflow-api    v1
```

---

# 4. Build the Frontend Image

```bash
docker build -t taskflow-frontend:v1 ./frontend
```

Check the images:

```bash
docker images | grep taskflow
```

You should now have:

```text
taskflow-api         v1
taskflow-frontend    v1
```

---

# 5. Create the Docker Network

Create a dedicated network for TaskFlow:

```bash
docker network create taskflow-network
```

Verify:

```bash
docker network ls
```

All TaskFlow containers will join this network.

```text
taskflow-network
       │
       ├── taskflow-frontend
       ├── taskflow-api
       ├── taskflow-postgres
       └── taskflow-redis
```

Docker DNS allows containers on the same network to communicate using their container names.

---

# 6. Create PostgreSQL Persistent Storage

Create the volume:

```bash
docker volume create taskflow-postgres-data
```

Verify:

```bash
docker volume ls
```

The volume preserves PostgreSQL data even if the PostgreSQL container is removed.

---

# 7. Start PostgreSQL

Run PostgreSQL:

```bash
docker run -d \
  --name taskflow-postgres \
  --network taskflow-network \
  -e POSTGRES_DB=taskflow \
  -e POSTGRES_USER=taskflow \
  -e POSTGRES_PASSWORD=taskflow123 \
  -v taskflow-postgres-data:/var/lib/postgresql/data \
  postgres:17-alpine
```

Check the container:

```bash
docker ps
```

Check PostgreSQL logs:

```bash
docker logs taskflow-postgres
```

PostgreSQL should eventually report that it is ready to accept connections.

---

# 8. Start Redis

Run Redis:

```bash
docker run -d \
  --name taskflow-redis \
  --network taskflow-network \
  redis:7-alpine
```

Check:

```bash
docker ps
```

Test Redis:

```bash
docker exec -it taskflow-redis redis-cli ping
```

Expected response:

```text
PONG
```

---

# 9. Start the TaskFlow API

The API needs access to both PostgreSQL and Redis.

Because these services are running in separate containers, do **not** configure:

```text
DB_HOST=localhost
```

Instead, use the PostgreSQL container name:

```text
DB_HOST=taskflow-postgres
```

The same applies to Redis:

```text
REDIS_HOST=taskflow-redis
```

Run the API:

```bash
docker run -d \
  --name taskflow-api \
  --network taskflow-network \
  -p 5000:5000 \
  -e PORT=5000 \
  -e DB_HOST=taskflow-postgres \
  -e DB_PORT=5432 \
  -e DB_NAME=taskflow \
  -e DB_USER=taskflow \
  -e DB_PASSWORD=taskflow123 \
  -e REDIS_HOST=taskflow-redis \
  -e REDIS_PORT=6379 \
  taskflow-api:v1
```

Check:

```bash
docker ps
```

View API logs:

```bash
docker logs taskflow-api
```

Follow logs continuously:

```bash
docker logs -f taskflow-api
```

Press:

```text
CTRL + C
```

to stop following the logs.

This does **not** stop the container.

---

# 10. Test the API

## Health Check

```bash
curl http://localhost:5000/health
```

This verifies that the API process is alive.

---

## Readiness Check

```bash
curl http://localhost:5000/ready
```

The readiness endpoint checks whether the API can communicate with its dependencies.

A healthy response should indicate that PostgreSQL and Redis are available.

Conceptually:

```text
/health
    │
    └── Is the application alive?


/ready
    │
    └── Is the application ready to serve traffic?
```

---

## Get Tasks

```bash
curl http://localhost:5000/api/tasks
```

---

## Prometheus Metrics

```bash
curl http://localhost:5000/metrics
```

This endpoint will later be scraped by Prometheus when monitoring is introduced.

---

# 11. Start the Frontend

The frontend proxies all `/api/` requests to the backend API. The backend URL is configured via the `API_URL` environment variable.

Run:

```bash
docker run -d \
  --name taskflow-frontend \
  --network taskflow-network \
  -p 3000:80 \
  -e API_URL=http://taskflow-api:5000/api \
  taskflow-frontend:v1
```

The `API_URL` can be customized for different environments. For example, when deploying to Kubernetes or a remote server, use the appropriate URL.

Check all containers:

```bash
docker ps
```

You should now have:

```text
taskflow-frontend
taskflow-api
taskflow-postgres
taskflow-redis
```

---

# 12. Frontend Environment Variables

The frontend uses the `API_URL` environment variable to configure where the backend API is located. This is substituted into the nginx configuration at container startup.

### Default Configuration (Docker Compose / Local)

```bash
API_URL=http://taskflow-api:5000/api
```

Uses the container name `taskflow-api` (resolves via Docker DNS on the `taskflow-network`).

### Remote Server Configuration

If deploying to a remote server (e.g., EC2):

```bash
docker run -d \
  --name taskflow-frontend \
  --network taskflow-network \
  -p 3000:80 \
  -e API_URL=http://YOUR_SERVER_IP:5000/api \
  taskflow-frontend:v1
```

### Kubernetes Configuration

For Kubernetes deployments:

```yaml
containers:
  - name: frontend
    image: taskflow-frontend:v1
    env:
      - name: API_URL
        value: "http://taskflow-api-service:5000/api"
    ports:
      - containerPort: 80
```

---

# 13. Access TaskFlow

On your local machine:

```text
http://localhost:3000
```

The API is available at:

```text
http://localhost:5000
```

If TaskFlow is running on a remote Linux server or EC2 instance, use:

```text
http://SERVER-IP:3000
```

Ensure the required firewall/security-group rules allow the necessary ports.

---

# 14. Inspect the Docker Network

Run:

```bash
docker network inspect taskflow-network
```

You should find the TaskFlow containers attached to the network.

Conceptually:

```text
                    taskflow-network
                           │
           ┌───────────────┼────────────────┐
           │               │                │
           ▼               ▼                ▼
      Frontend            API           PostgreSQL
                           │
                           ▼
                         Redis
```

---

# 15. Enter the API Container

```bash
docker exec -it taskflow-api sh
```

You are now inside the running API container.

Exit:

```bash
exit
```

---

# 16. Enter the Redis Container

```bash
docker exec -it taskflow-redis sh
```

You can also directly access Redis CLI:

```bash
docker exec -it taskflow-redis redis-cli
```

Inside Redis:

```text
PING
```

Expected:

```text
PONG
```

Exit:

```text
exit
```

---

# 17. Connect to PostgreSQL

Connect directly:

```bash
docker exec -it taskflow-postgres \
  psql -U taskflow -d taskflow
```

List tables:

```sql
\dt
```

View tasks:

```sql
SELECT * FROM tasks;
```

Exit PostgreSQL:

```sql
\q
```

---

# 18. View Container Resource Usage

```bash
docker stats
```

This displays CPU, memory and network usage for the running containers.

Press:

```text
CTRL + C
```

to exit.

---

# 19. Inspect a Container

For example:

```bash
docker inspect taskflow-api
```

You can inspect PostgreSQL:

```bash
docker inspect taskflow-postgres
```

Or Redis:

```bash
docker inspect taskflow-redis
```

---

# 20. View Logs

API:

```bash
docker logs taskflow-api
```

PostgreSQL:

```bash
docker logs taskflow-postgres
```

Redis:

```bash
docker logs taskflow-redis
```

Frontend:

```bash
docker logs taskflow-frontend
```

---

# 21. Stop the Application

Stop all TaskFlow containers:

```bash
docker stop \
  taskflow-frontend \
  taskflow-api \
  taskflow-redis \
  taskflow-postgres
```

Check:

```bash
docker ps
```

Stopped containers can be viewed with:

```bash
docker ps -a
```

---

# 22. Start the Application Again

Start PostgreSQL first:

```bash
docker start taskflow-postgres
```

Then Redis:

```bash
docker start taskflow-redis
```

Then the API:

```bash
docker start taskflow-api
```

Then the frontend:

```bash
docker start taskflow-frontend
```

Or:

```bash
docker start \
  taskflow-postgres \
  taskflow-redis \
  taskflow-api \
  taskflow-frontend
```

Check:

```bash
docker ps
```

---

# 23. Remove the Containers

```bash
docker rm -f \
  taskflow-frontend \
  taskflow-api \
  taskflow-redis \
  taskflow-postgres
```

Check:

```bash
docker ps -a
```

---

# 24. Verify PostgreSQL Data Still Exists

Even after removing the PostgreSQL container, the volume remains:

```bash
docker volume ls
```

You should still see:

```text
taskflow-postgres-data
```

This demonstrates an important Docker principle:

```text
Container Lifecycle
        ≠
Data Lifecycle
```

The container can be destroyed while persistent data remains.

---

# 25. Delete the PostgreSQL Data

> Warning: this permanently deletes the database data stored in the Docker volume.

```bash
docker volume rm taskflow-postgres-data
```

---

# 26. Delete the Docker Network

After removing the containers:

```bash
docker network rm taskflow-network
```

---

# 27. Remove TaskFlow Images

```bash
docker rmi taskflow-api:v1
```

```bash
docker rmi taskflow-frontend:v1
```

---

# Useful Docker Commands

| Task                | Command                                   |
| ------------------- | ----------------------------------------- |
| Running containers  | `docker ps`                               |
| All containers      | `docker ps -a`                            |
| Images              | `docker images`                           |
| Networks            | `docker network ls`                       |
| Volumes             | `docker volume ls`                        |
| API logs            | `docker logs taskflow-api`                |
| Follow API logs     | `docker logs -f taskflow-api`             |
| Inspect API         | `docker inspect taskflow-api`             |
| Enter API           | `docker exec -it taskflow-api sh`         |
| Container resources | `docker stats`                            |
| Inspect network     | `docker network inspect taskflow-network` |

---

# Final Docker Architecture

After completing the lab, the environment should look like:

```text
                           USER
                            │
                            │ :3000
                            ▼
                 ┌────────────────────┐
                 │ TaskFlow Frontend  │
                 │       NGINX        │
                 └──────────┬─────────┘
                            │
                            │ HTTP
                            ▼
                 ┌────────────────────┐
                 │    TaskFlow API    │
                 │   Node + Express   │
                 │       :5000        │
                 └──────────┬─────────┘
                            │
                   ┌────────┴────────┐
                   │                 │
                   ▼                 ▼
          ┌────────────────┐   ┌─────────────┐
          │   PostgreSQL   │   │    Redis    │
          │      :5432     │   │    :6379    │
          └───────┬────────┘   └─────────────┘
                  │
                  ▼
       taskflow-postgres-data
            Docker Volume


All containers:
        │
        ▼
 taskflow-network
```

# Learning Objectives

After completing this Docker-only deployment, you should understand:

* Docker images
* Docker containers
* Dockerfiles
* Image building
* Port publishing
* Environment variables
* Docker networking
* Docker DNS/service discovery
* Persistent volumes
* Container logs
* Container inspection
* Container execution
* Basic troubleshooting
* Multi-container applications
* Container lifecycle
* Data persistence

The next stage of TaskFlow will replace these individual `docker run` commands with **Docker Compose**, before migrating the same application to Kubernetes.
