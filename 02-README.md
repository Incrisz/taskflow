# TaskFlow — Kubernetes Architecture, Core Objects, Deployments, Services & Scaling

This lab migrates the TaskFlow application from standalone Docker containers into Kubernetes.

It covers:

* **Module 3: Kubernetes Architecture and Core Objects**
* **Module 4: Deployments, Services, and Scaling**

---

# Kubernetes Deployment Order

Run these commands from the repository root after preparing your cluster and loading the application images. The numbered folders show the dependency order:

```bash
kubectl apply -f kubernetes/00-namespace.yaml
kubectl apply -f kubernetes/01-config/
kubectl apply -f kubernetes/02-rbac/
kubectl apply -f kubernetes/03-postgres/
kubectl apply -f kubernetes/04-redis/
kubectl apply -f kubernetes/05-backend/
kubectl apply -f kubernetes/06-frontend/
```

| Step | File or folder | Purpose |
| --- | --- | --- |
| 00 | `00-namespace.yaml` | Create the namespace first |
| 01 | `01-config/` | Create the ConfigMap and database Secret |
| 02 | `02-rbac/` | Create the ServiceAccount referenced by the API |
| 03 | `03-postgres/` | Deploy PostgreSQL and its Service and storage |
| 04 | `04-redis/` | Deploy Redis and its Service |
| 05 | `05-backend/` | Deploy the API and its Service |
| 06 | `06-frontend/` | Deploy the frontend and its Service |

The API and Redis manifests each contain both a Deployment and a Service. The later exercises explain these objects separately; edit the corresponding document within the existing manifest instead of replacing the whole file with a partial example.

The numbers indicate apply order, not readiness: workloads may still be starting after each command completes. PostgreSQL needs suitable persistent storage and database initialization; the frontend needs its `API_URL` configured before the complete application can work.

---

# Learning Objectives

By the end of this lab, you should be able to:

* Explain Kubernetes cluster architecture
* Understand the Control Plane and Worker Nodes
* Work with Namespaces, Pods, Deployments and Services
* Understand labels and selectors
* Deploy TaskFlow to Kubernetes
* Understand Kubernetes service discovery
* Expose applications using Services
* Scale applications manually
* Understand Kubernetes self-healing
* Perform rolling updates
* Monitor rollout status
* View deployment revision history
* Roll back failed deployments
* Understand ReplicaSets
* Troubleshoot Pods and Services

---

# 1. TaskFlow Architecture

TaskFlow consists of:

```text
Frontend
   │
   ▼
API
   │
   ├────► PostgreSQL
   │
   └────► Redis
```

In Kubernetes, this becomes:

```text
                     Kubernetes Cluster
                            │
                     taskflow namespace
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
    Frontend              API              PostgreSQL
   Deployment          Deployment            Pod
        │                   │
        ▼                   ▼
     Service             Service
                            │
                            ▼
                          Redis
                           Pod
```

Later modules will improve PostgreSQL storage, configuration, security and application packaging.

---

# 2. Kubernetes Architecture

A Kubernetes cluster consists primarily of:

```text
                  Kubernetes Cluster
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
  CONTROL PLANE                      WORKER NODES
        │                                 │
        ├── API Server                    ├── kubelet
        ├── Scheduler                     ├── kube-proxy
        ├── Controller Manager            ├── Container Runtime
        └── etcd                          └── Pods
```

## Control Plane

The Control Plane manages the cluster.

### API Server

The API Server is the main entry point into Kubernetes.

When you execute:

```bash
kubectl get pods
```

`kubectl` communicates with the Kubernetes API Server.

Conceptually:

```text
kubectl
   │
   ▼
API Server
   │
   ▼
Kubernetes Cluster
```

### etcd

`etcd` stores the cluster's state and configuration.

It stores information about objects such as:

```text
Pods
Deployments
Services
Namespaces
ConfigMaps
Secrets
Nodes
```

### Scheduler

The scheduler determines which worker node should run a newly created Pod.

```text
New Pod
   │
   ▼
Scheduler
   │
   ├── Node 1
   ├── Node 2
   └── Node 3
```

The decision considers factors including resource requests, scheduling constraints and node availability.

### Controller Manager

Controllers continuously compare:

```text
Desired State
      │
      ▼
Actual State
```

and attempt to reconcile differences.

For example:

```text
Desired replicas = 3

Actual replicas = 2
```

Kubernetes creates another Pod.

This reconciliation model is one of the foundations of Kubernetes.

---

# 3. Worker Nodes

Worker nodes run application workloads.

Important components include:

```text
Worker Node
│
├── kubelet
├── kube-proxy
├── Container Runtime
│
└── Pods
```

The **kubelet** communicates with the Control Plane and ensures assigned Pods are running.

---

# 4. Verify the Kubernetes Cluster

Check the cluster:

```bash
kubectl cluster-info
```

Check nodes:

```bash
kubectl get nodes
```

For more information:

```bash
kubectl get nodes -o wide
```

Expected example:

```text
NAME                 STATUS   ROLES
taskflow-control     Ready    control-plane
taskflow-worker      Ready    <none>
taskflow-worker2     Ready    <none>
```

Your actual node names may be different.

---

# 5. View Existing Kubernetes Objects

```bash
kubectl get pods -A
```

This shows Pods across all namespaces.

Check namespaces:

```bash
kubectl get namespaces
```

Short form:

```bash
kubectl get ns
```

---

# 6. Create the TaskFlow Namespace

Create:

```yaml
apiVersion: v1
kind: Namespace

metadata:
  name: taskflow
```

Save as:

```text
kubernetes/00-namespace.yaml
```

Apply:

```bash
kubectl apply -f kubernetes/00-namespace.yaml
```

Verify:

```bash
kubectl get namespaces
```

You should see:

```text
taskflow
```

From this point, TaskFlow resources will be isolated inside this namespace.

---

# 7. Understanding Kubernetes Objects

Most Kubernetes YAML manifests contain four major sections:

```yaml
apiVersion:

kind:

metadata:

spec:
```

For example:

```yaml
apiVersion: v1
kind: Pod

metadata:
  name: example

spec:
  containers:
    - name: nginx
      image: nginx
```

## apiVersion

Specifies the Kubernetes API version.

## kind

Defines the object type.

Examples:

```text
Pod
Service
Deployment
Namespace
ConfigMap
Secret
```

## metadata

Identifies the object.

For example:

```yaml
metadata:
  name: taskflow-api
  namespace: taskflow
```

## spec

Describes the desired state.

---

# 8. Your First TaskFlow Pod

Before using Deployments, create one API Pod manually.

```yaml
apiVersion: v1
kind: Pod

metadata:
  name: taskflow-api-pod
  namespace: taskflow

  labels:
    app: taskflow-api

spec:

  containers:

    - name: api
      image: taskflow-api:v1

      ports:
        - containerPort: 5000
```

Apply:

```bash
kubectl apply -f api-pod.yaml
```

Check:

```bash
kubectl get pods -n taskflow
```

More details:

```bash
kubectl get pods -n taskflow -o wide
```

Inspect:

```bash
kubectl describe pod taskflow-api-pod -n taskflow
```

Logs:

```bash
kubectl logs taskflow-api-pod -n taskflow
```

---

# 9. Important: Local Docker Images

If your Kubernetes cluster is running with Kind, the Docker image on your host is not automatically available inside the Kind nodes.

Load the image:

```bash
kind load docker-image taskflow-api:v1
```

For the frontend:

```bash
kind load docker-image taskflow-frontend:v1
```

If your cluster has a specific Kind cluster name:

```bash
kind load docker-image taskflow-api:v1 --name <cluster-name>
```

and:

```bash
kind load docker-image taskflow-frontend:v1 --name <cluster-name>
```

Verify Pods afterward:

```bash
kubectl get pods -n taskflow
```

---

# 10. Why Pods Alone Are Not Enough

Delete the manually created Pod:

```bash
kubectl delete pod taskflow-api-pod -n taskflow
```

Check:

```bash
kubectl get pods -n taskflow
```

The Pod is gone.

Nothing recreates it.

This demonstrates why production applications should generally not be managed as standalone Pods.

We need a controller.

---

# MODULE 4 — DEPLOYMENTS, SERVICES AND SCALING

# 11. Create the API Deployment

Create:

```text
kubernetes/05-backend/api.yaml
```

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: taskflow-api
  namespace: taskflow

spec:

  replicas: 2

  selector:
    matchLabels:
      app: taskflow-api

  template:

    metadata:
      labels:
        app: taskflow-api

    spec:

      containers:

        - name: api
          image: taskflow-api:v1

          imagePullPolicy: IfNotPresent

          ports:

            - containerPort: 5000
```

Apply:

```bash
kubectl apply -f kubernetes/05-backend/api.yaml
```

Check:

```bash
kubectl get deployments -n taskflow
```

Short form:

```bash
kubectl get deploy -n taskflow
```

Check Pods:

```bash
kubectl get pods -n taskflow
```

You should have two API Pods.

---

# 12. Deployment → ReplicaSet → Pods

Run:

```bash
kubectl get deployment -n taskflow
```

Then:

```bash
kubectl get replicasets -n taskflow
```

Short form:

```bash
kubectl get rs -n taskflow
```

Then:

```bash
kubectl get pods -n taskflow
```

The relationship is:

```text
Deployment
    │
    ▼
ReplicaSet
    │
    ├────► Pod
    │
    └────► Pod
```

You normally manage the **Deployment**, rather than directly managing its ReplicaSet or Pods.

---

# 13. Demonstrate Kubernetes Self-Healing

Check Pods:

```bash
kubectl get pods -n taskflow
```

Copy one API Pod name and delete it:

```bash
kubectl delete pod <pod-name> -n taskflow
```

Immediately watch:

```bash
kubectl get pods -n taskflow -w
```

Kubernetes creates another Pod.

Why?

The Deployment says:

```yaml
replicas: 2
```

Kubernetes sees:

```text
Desired = 2

Actual = 1
```

and reconciles:

```text
Desired = 2
Actual  = 2
```

This demonstrates **self-healing and desired state**.

Press:

```text
CTRL + C
```

to stop watching.

---

# 14. Labels

Check Pod labels:

```bash
kubectl get pods -n taskflow --show-labels
```

The API Pods should have:

```text
app=taskflow-api
```

Filter using the label:

```bash
kubectl get pods \
  -n taskflow \
  -l app=taskflow-api
```

Labels become extremely important when Services are introduced.

---

# 15. Create the API Service

Pods are temporary.

Their IP addresses can change when they are recreated.

Therefore, applications should not depend directly on Pod IP addresses.

Create:

```text
kubernetes/05-backend/api.yaml
```

```yaml
apiVersion: v1
kind: Service

metadata:
  name: taskflow-api
  namespace: taskflow

spec:

  selector:
    app: taskflow-api

  ports:

    - protocol: TCP
      port: 5000
      targetPort: 5000

  type: ClusterIP
```

Apply:

```bash
kubectl apply -f kubernetes/05-backend/api.yaml
```

Check:

```bash
kubectl get services -n taskflow
```

Short form:

```bash
kubectl get svc -n taskflow
```

Architecture:

```text
                 taskflow-api Service
                        │
                 selector:
                 app=taskflow-api
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
          API Pod             API Pod
```

The Service provides a stable network endpoint.

---

# 16. Service Discovery

Inside the same namespace, other workloads can reach the API using:

```text
taskflow-api
```

For example:

```text
http://taskflow-api:5000
```

Kubernetes DNS resolves the Service name.

Conceptually:

```text
Frontend Pod
      │
      ▼
taskflow-api
      │
      ▼
Kubernetes DNS
      │
      ▼
API Service
      │
      ▼
API Pods
```

---

# 17. Service Endpoints

Check:

```bash
kubectl get endpoints -n taskflow
```

You can specifically inspect:

```bash
kubectl get endpoints taskflow-api -n taskflow
```

The endpoint addresses correspond to Pods selected by:

```yaml
selector:
  app: taskflow-api
```

This is very important for troubleshooting.

If a Service exists but has no endpoints, always investigate its selector and the Pod labels.

---

# 18. Describe the Service

```bash
kubectl describe service taskflow-api -n taskflow
```

Look at:

```text
Selector
IP
Port
TargetPort
Endpoints
```

---

# 19. Scale the API

Current state:

```text
API

● ●
```

Scale to five replicas:

```bash
kubectl scale deployment taskflow-api \
  --replicas=5 \
  -n taskflow
```

Check:

```bash
kubectl get pods -n taskflow
```

You should now have:

```text
● ● ● ● ●
```

Check Deployment:

```bash
kubectl get deployment taskflow-api -n taskflow
```

Check ReplicaSet:

```bash
kubectl get rs -n taskflow
```

---

# 20. Scale Down

```bash
kubectl scale deployment taskflow-api \
  --replicas=2 \
  -n taskflow
```

Watch:

```bash
kubectl get pods -n taskflow -w
```

Kubernetes terminates unnecessary Pods until:

```text
Desired = 2
Actual  = 2
```

---

# 21. Declarative vs Imperative Scaling

This command is imperative:

```bash
kubectl scale deployment taskflow-api \
  --replicas=4 \
  -n taskflow
```

You are directly telling Kubernetes what to do.

The YAML approach is declarative:

```yaml
spec:
  replicas: 4
```

Then:

```bash
kubectl apply -f kubernetes/05-backend/api.yaml
```

You describe the desired state and Kubernetes reconciles toward it.

---

# 22. Deploy Redis

Create:

```text
kubernetes/04-redis/redis.yaml
```

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: redis
  namespace: taskflow

spec:

  replicas: 1

  selector:

    matchLabels:
      app: redis

  template:

    metadata:

      labels:
        app: redis

    spec:

      containers:

        - name: redis
          image: redis:7-alpine

          ports:

            - containerPort: 6379
```

Apply:

```bash
kubectl apply -f kubernetes/04-redis/redis.yaml
```

---

# 23. Create Redis Service

```yaml
apiVersion: v1
kind: Service

metadata:
  name: redis
  namespace: taskflow

spec:

  selector:
    app: redis

  ports:

    - port: 6379
      targetPort: 6379

  type: ClusterIP
```

Apply:

```bash
kubectl apply -f kubernetes/04-redis/redis.yaml
```

Verify:

```bash
kubectl get pods -n taskflow
```

```bash
kubectl get svc -n taskflow
```

---

# 24. Deploy PostgreSQL

For Modules 3 and 4, PostgreSQL can be introduced as a simple workload first.

Persistent storage and the StatefulSet design can be explored in greater depth in the storage module.

Create the PostgreSQL workload according to the supplied TaskFlow Kubernetes manifests.

Apply:

```bash
kubectl apply -f kubernetes/03-postgres/
```

Check:

```bash
kubectl get pods -n taskflow
```

Check Service:

```bash
kubectl get svc -n taskflow
```

The API should eventually communicate using:

```text
postgres:5432
```

rather than a Pod IP.

---

# 25. Deploy the Frontend

Load the frontend image into Kind if necessary:

```bash
kind load docker-image taskflow-frontend:v1
```

Apply:

```bash
kubectl apply -f kubernetes/06-frontend/
```

Check:

```bash
kubectl get pods -n taskflow
```

You should eventually have workloads resembling:

```text
taskflow-frontend-xxxxx
taskflow-api-xxxxx
taskflow-api-yyyyy
postgres-xxxxx
redis-xxxxx
```

---

# 26. View Everything in the Namespace

Instead of running several commands:

```bash
kubectl get all -n taskflow
```

This provides a useful overview of many workload and networking resources.

For more detail:

```bash
kubectl get pods,svc,deploy,rs -n taskflow -o wide
```

---

# 27. Expose the Frontend for Testing

For a simple local lab, use port forwarding:

```bash
kubectl port-forward \
  service/taskflow-frontend \
  3000:80 \
  -n taskflow
```

Open:

```text
http://localhost:3000
```

Keep that terminal running while testing.

Press:

```text
CTRL + C
```

to stop the port forward.

Ingress will be covered separately.

---

# 28. Rolling Updates

Suppose we build:

```text
taskflow-api:v2
```

Load it into Kind:

```bash
kind load docker-image taskflow-api:v2
```

Update the Deployment:

```bash
kubectl set image \
  deployment/taskflow-api \
  api=taskflow-api:v2 \
  -n taskflow
```

Watch the rollout:

```bash
kubectl rollout status \
  deployment/taskflow-api \
  -n taskflow
```

Watch Pods:

```bash
kubectl get pods -n taskflow -w
```

Conceptually:

```text
OLD VERSION

v1    v1    v1


        ↓ Rolling Update


v1    v1    v2


        ↓


v1    v2    v2


        ↓


v2    v2    v2
```

Kubernetes progressively replaces old Pods.

---

# 29. Check Deployment Image

```bash
kubectl describe deployment taskflow-api -n taskflow
```

Or:

```bash
kubectl get deployment taskflow-api \
  -n taskflow \
  -o wide
```

---

# 30. Deployment History

```bash
kubectl rollout history \
  deployment/taskflow-api \
  -n taskflow
```

This displays Deployment revisions.

---

# 31. Roll Back

Suppose `v2` has a problem.

Rollback:

```bash
kubectl rollout undo \
  deployment/taskflow-api \
  -n taskflow
```

Monitor:

```bash
kubectl rollout status \
  deployment/taskflow-api \
  -n taskflow
```

Check:

```bash
kubectl get pods -n taskflow
```

---

# 32. Pause and Resume a Rollout

Pause:

```bash
kubectl rollout pause \
  deployment/taskflow-api \
  -n taskflow
```

Resume:

```bash
kubectl rollout resume \
  deployment/taskflow-api \
  -n taskflow
```

---

# 33. Pod Troubleshooting Commands

When a Pod fails, start with:

```bash
kubectl get pods -n taskflow
```

Then:

```bash
kubectl describe pod <pod-name> -n taskflow
```

Then:

```bash
kubectl logs <pod-name> -n taskflow
```

For previous crashed container logs:

```bash
kubectl logs <pod-name> \
  -n taskflow \
  --previous
```

Check events:

```bash
kubectl get events \
  -n taskflow \
  --sort-by=.metadata.creationTimestamp
```

---

# 34. Execute Commands Inside a Pod

```bash
kubectl exec -it \
  <pod-name> \
  -n taskflow \
  -- sh
```

This is useful for investigating:

```text
Environment variables
DNS
Network connectivity
Files
Application processes
```

Exit:

```bash
exit
```

---

# 35. Inspect Environment Variables

For example:

```bash
kubectl exec \
  <api-pod-name> \
  -n taskflow \
  -- env
```

---

# 36. Kubernetes DNS Test

Start a temporary troubleshooting Pod:

```bash
kubectl run network-test \
  --image=busybox:1.36 \
  --restart=Never \
  -n taskflow \
  -- sleep 3600
```

Enter:

```bash
kubectl exec -it network-test \
  -n taskflow \
  -- sh
```

Test DNS:

```bash
nslookup taskflow-api
```

Test Redis:

```bash
nslookup redis
```

Test PostgreSQL:

```bash
nslookup postgres
```

Exit:

```bash
exit
```

Delete the troubleshooting Pod:

```bash
kubectl delete pod network-test -n taskflow
```

---

# 37. Controlled Failure Lab — Self-Healing

Check:

```bash
kubectl get pods -n taskflow
```

Delete one API Pod:

```bash
kubectl delete pod <api-pod> -n taskflow
```

Immediately run:

```bash
kubectl get pods -n taskflow -w
```

Question:

> Why did Kubernetes recreate this Pod, but it did not recreate the standalone Pod we created earlier?

Answer:

The API Pods are managed by a Deployment/ReplicaSet that maintains the desired replica count.

---

# 38. Controlled Failure Lab — Broken Service

Temporarily change:

```yaml
selector:
  app: taskflow-api
```

to:

```yaml
selector:
  app: wrong-api
```

Apply:

```bash
kubectl apply -f kubernetes/05-backend/api.yaml
```

The Service still exists:

```bash
kubectl get svc -n taskflow
```

But inspect:

```bash
kubectl get endpoints taskflow-api -n taskflow
```

There should be no valid backend endpoints.

Investigate:

```bash
kubectl describe service taskflow-api -n taskflow
```

Then:

```bash
kubectl get pods \
  -n taskflow \
  --show-labels
```

Students should discover:

```text
Service selector:

app=wrong-api


Pod label:

app=taskflow-api
```

Fix the selector and reapply:

```bash
kubectl apply -f kubernetes/05-backend/api.yaml
```

Check:

```bash
kubectl get endpoints taskflow-api -n taskflow
```

The endpoints should return.

---

# 39. Controlled Failure Lab — ImagePullBackOff

Change:

```yaml
image: taskflow-api:v1
```

to a nonexistent image:

```yaml
image: taskflow-api:v999
```

Apply:

```bash
kubectl apply -f kubernetes/05-backend/api.yaml
```

Check:

```bash
kubectl get pods -n taskflow
```

You may see:

```text
ImagePullBackOff
```

Investigate:

```bash
kubectl describe pod <pod-name> -n taskflow
```

Correct the image and apply again.

---

# 40. Controlled Failure Lab — Application Logs

Introduce an application configuration error.

Check:

```bash
kubectl get pods -n taskflow
```

Then:

```bash
kubectl logs <api-pod> -n taskflow
```

If the container repeatedly crashes:

```bash
kubectl logs <api-pod> \
  -n taskflow \
  --previous
```

This introduces the basic troubleshooting workflow:

```text
kubectl get
      │
      ▼
kubectl describe
      │
      ▼
kubectl logs
      │
      ▼
kubectl get events
      │
      ▼
kubectl exec
```

---

# 41. Useful Commands

| Task                | Command                                                          |
| ------------------- | ---------------------------------------------------------------- |
| Cluster information | `kubectl cluster-info`                                           |
| Nodes               | `kubectl get nodes`                                              |
| Namespaces          | `kubectl get ns`                                                 |
| TaskFlow Pods       | `kubectl get pods -n taskflow`                                   |
| Detailed Pods       | `kubectl get pods -n taskflow -o wide`                           |
| Deployments         | `kubectl get deploy -n taskflow`                                 |
| ReplicaSets         | `kubectl get rs -n taskflow`                                     |
| Services            | `kubectl get svc -n taskflow`                                    |
| Endpoints           | `kubectl get endpoints -n taskflow`                              |
| All common objects  | `kubectl get all -n taskflow`                                    |
| Pod details         | `kubectl describe pod <pod> -n taskflow`                         |
| Pod logs            | `kubectl logs <pod> -n taskflow`                                 |
| Previous logs       | `kubectl logs <pod> -n taskflow --previous`                      |
| Enter Pod           | `kubectl exec -it <pod> -n taskflow -- sh`                       |
| Events              | `kubectl get events -n taskflow`                                 |
| Scale               | `kubectl scale deployment taskflow-api --replicas=5 -n taskflow` |
| Rollout status      | `kubectl rollout status deployment/taskflow-api -n taskflow`     |
| History             | `kubectl rollout history deployment/taskflow-api -n taskflow`    |
| Rollback            | `kubectl rollout undo deployment/taskflow-api -n taskflow`       |

---

# 42. Final Architecture

At the end of Modules 3 and 4:

```text
                           USER
                            │
                            ▼
                  Frontend Service
                            │
                            ▼
                  Frontend Deployment
                            │
                            ▼
                    Frontend Pods
                            │
                            │
                            ▼
                     API Service
                  taskflow-api:5000
                            │
                 ┌──────────┼──────────┐
                 │          │          │
                 ▼          ▼          ▼
              API Pod    API Pod    API Pod
                 │
          ┌──────┴──────────┐
          │                 │
          ▼                 ▼
    PostgreSQL Service   Redis Service
          │                 │
          ▼                 ▼
      PostgreSQL           Redis
       Workload           Workload
```

All application resources reside inside:

```text
Namespace: taskflow
```

---

# 43. Core Concepts Covered

## Module 3 — Kubernetes Architecture and Core Objects

You should now understand:

* Control Plane
* Worker Nodes
* API Server
* etcd
* Scheduler
* Controller Manager
* kubelet
* Pods
* Namespaces
* Labels
* Selectors
* Desired state
* Declarative configuration
* `kubectl`
* Kubernetes YAML structure

## Module 4 — Deployments, Services and Scaling

You should now understand:

* Deployments
* ReplicaSets
* Replicas
* Self-healing
* ClusterIP Services
* Service discovery
* Kubernetes DNS
* Service selectors
* Service endpoints
* Manual scaling
* Rolling updates
* Deployment history
* Rollbacks
* Basic workload troubleshooting

---

# 44. Cleanup

Delete the entire TaskFlow environment:

```bash
kubectl delete namespace taskflow
```

Verify:

```bash
kubectl get namespaces
```

Because all TaskFlow resources were created inside the `taskflow` namespace, deleting the namespace removes the resources contained within it.

---

# Next Module

The next stage extends this environment with:

```text
TaskFlow
   │
   ├── Persistent Storage
   ├── ConfigMaps
   ├── Secrets
   └── Helm
```

This prepares the application for:

**Module 5 — ConfigMaps, Secrets, Persistent Configuration and Helm Charts.**
