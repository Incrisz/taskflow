# Kubernetes Cluster Administration, Monitoring, Logging & Troubleshooting Commands

This document contains basic Kubernetes commands used for:

- Cluster Administration
- Resource Management
- Monitoring
- Logging
- Pod Troubleshooting

---

# 1. Cluster Administration

## Check Kubernetes Cluster Information

View cluster details:

```bash
kubectl cluster-info
```

Example output:

```
Kubernetes control plane is running
CoreDNS is running
```

---

## View Cluster Nodes

List all nodes:

```bash
kubectl get nodes
```

Detailed node information:

```bash
kubectl get nodes -o wide
```

Describe a node:

```bash
kubectl describe node <node-name>
```

Shows:

- CPU capacity
- Memory capacity
- Running pods
- Node conditions
- Labels
- Taints

---

## View Kubernetes Version

Client and server version:

```bash
kubectl version
```

Short version:

```bash
kubectl version --short
```

---

## View Current Kubernetes Context

Show current cluster:

```bash
kubectl config current-context
```

List available contexts:

```bash
kubectl config get-contexts
```

Switch context:

```bash
kubectl config use-context <context-name>
```

---

# 2. Namespace Administration

## List Namespaces

```bash
kubectl get namespaces
```

or:

```bash
kubectl get ns
```

---

## Create Namespace

```bash
kubectl create namespace <namespace-name>
```

Example:

```bash
kubectl create namespace taskflow
```

---

## Delete Namespace

```bash
kubectl delete namespace <namespace-name>
```

---

## View Resources Inside Namespace

```bash
kubectl get all -n <namespace>
```

Example:

```bash
kubectl get all -n taskflow
```

---

# 3. Resource Management

## View All Resources

Current namespace:

```bash
kubectl get all
```

Specific namespace:

```bash
kubectl get all -n taskflow
```

All namespaces:

```bash
kubectl get all -A
```

---

## Apply Kubernetes Configuration

Create/update resources:

```bash
kubectl apply -f <file.yaml>
```

Example:

```bash
kubectl apply -f deployment.yaml
```

Apply directory:

```bash
kubectl apply -f .
```

---

## Delete Resources

Delete using YAML:

```bash
kubectl delete -f <file.yaml>
```

Delete resource directly:

```bash
kubectl delete pod <pod-name>
```

---

# 4. Deployment Administration

## List Deployments

```bash
kubectl get deployments
```

Namespace:

```bash
kubectl get deployments -n taskflow
```

---

## Describe Deployment

```bash
kubectl describe deployment <deployment-name>
```

Shows:

- Replica status
- Pod template
- Events
- Strategy

---

## Check Deployment Status

```bash
kubectl rollout status deployment/<deployment-name>
```

Example:

```bash
kubectl rollout status deployment/taskflow-api
```

---

## View Deployment History

```bash
kubectl rollout history deployment/<deployment-name>
```

---

## Restart Deployment

```bash
kubectl rollout restart deployment/<deployment-name>
```

Example:

```bash
kubectl rollout restart deployment/taskflow-api
```

---

## Scale Deployment

Increase replicas:

```bash
kubectl scale deployment <deployment-name> --replicas=3
```

Example:

```bash
kubectl scale deployment taskflow-api --replicas=3
```

---

# 5. Monitoring Kubernetes Resources

## Monitor Pods

List pods:

```bash
kubectl get pods
```

Watch changes:

```bash
kubectl get pods -w
```

Detailed view:

```bash
kubectl get pods -o wide
```

---

## Check Pod Status

Example:

```bash
kubectl get pods
```

Possible states:

```
Running
Pending
CrashLoopBackOff
ImagePullBackOff
Completed
Error
```

---

## Resource Usage

CPU and Memory usage:

```bash
kubectl top nodes
```

Example:

```
NAME        CPU    MEMORY
node-1      30%    40%
```

---

View Pod resource usage:

```bash
kubectl top pods
```

Specific namespace:

```bash
kubectl top pods -n taskflow
```

---

# 6. Monitoring Applications

## View Services

```bash
kubectl get services
```

or:

```bash
kubectl get svc
```

---

## Describe Service

```bash
kubectl describe service <service-name>
```

Shows:

- Cluster IP
- Ports
- Selector
- Endpoints

---

## Check Service Endpoints

```bash
kubectl get endpoints
```

Example:

```
postgres

10.244.1.10:5432
```

---

# 7. Logging

## View Pod Logs

Basic logs:

```bash
kubectl logs <pod-name>
```

Example:

```bash
kubectl logs taskflow-api-xxxxx
```

---

## Follow Logs Live

```bash
kubectl logs -f <pod-name>
```

Similar to:

```bash
tail -f logfile
```

---

## View Logs From Specific Container

For multi-container Pods:

```bash
kubectl logs <pod-name> -c <container-name>
```

---

## Previous Container Logs

Useful for crashed containers:

```bash
kubectl logs <pod-name> --previous
```

---

# 8. Troubleshooting Pods

## Describe Pod

The first troubleshooting command:

```bash
kubectl describe pod <pod-name>
```

Look at:

```
Events:
```

Common errors:

- FailedScheduling
- ImagePullBackOff
- CrashLoopBackOff
- FailedMount

---

## Check Pod Events

```bash
kubectl get events
```

Sort by time:

```bash
kubectl get events --sort-by=.metadata.creationTimestamp
```

Namespace:

```bash
kubectl get events -n taskflow
```

---

# 9. Common Pod Problems

## Pod Stuck Pending

Check:

```bash
kubectl describe pod <pod-name>
```

Possible causes:

- Not enough CPU
- Not enough memory
- Storage unavailable
- Node selector issue

---

## Pod CrashLoopBackOff

Meaning:

The container starts but crashes repeatedly.

Check logs:

```bash
kubectl logs <pod-name>
```

Previous crash:

```bash
kubectl logs <pod-name> --previous
```

Check details:

```bash
kubectl describe pod <pod-name>
```

---

## ImagePullBackOff

Meaning:

Kubernetes cannot download the container image.

Check:

```bash
kubectl describe pod <pod-name>
```

Possible causes:

- Wrong image name
- Private registry authentication
- Image does not exist

---

# 10. Accessing Containers

## Enter Running Container

Using bash:

```bash
kubectl exec -it <pod-name> -- bash
```

Using sh:

```bash
kubectl exec -it <pod-name> -- sh
```

---

## Execute Command Inside Container

Example:

```bash
kubectl exec <pod-name> -- ls
```

Check environment:

```bash
kubectl exec <pod-name> -- env
```

---

# 11. Networking Troubleshooting

## Check Service

```bash
kubectl get svc
```

---

## Test DNS Inside Pod

Enter pod:

```bash
kubectl exec -it <pod-name> -- sh
```

Test service:

```bash
nslookup postgres
```

or:

```bash
ping postgres
```

---

## Test Port Connectivity

Inside container:

```bash
curl http://service-name:port
```

Example:

```bash
curl http://taskflow-api:5000
```

---

# 12. Storage Troubleshooting

## View PersistentVolumeClaims

```bash
kubectl get pvc
```

---

## View PersistentVolumes

```bash
kubectl get pv
```

---

## Describe PVC

```bash
kubectl describe pvc <pvc-name>
```

Check:

- Storage class
- Binding status
- Events

---

# 13. RBAC Checks

## Check User Permission

Example:

```bash
kubectl auth can-i get pods
```

Check another user:

```bash
kubectl auth can-i get pods --as=<username>
```

Example:

```bash
kubectl auth can-i delete pods --as=developer
```

---

## View Roles

```bash
kubectl get roles
```

---

## View RoleBindings

```bash
kubectl get rolebindings
```

---

# 14. Useful Debugging Workflow

When a Pod fails:

## Step 1: Check status

```bash
kubectl get pods
```

---

## Step 2: Describe Pod

```bash
kubectl describe pod <pod-name>
```

---

## Step 3: Check Logs

```bash
kubectl logs <pod-name>
```

---

## Step 4: Check Events

```bash
kubectl get events
```

---

## Step 5: Enter Container

```bash
kubectl exec -it <pod-name> -- sh
```

---

# Quick Command Reference

| Task | Command |
|-|-|
| View nodes | `kubectl get nodes` |
| View pods | `kubectl get pods` |
| View services | `kubectl get svc` |
| View deployments | `kubectl get deployments` |
| View logs | `kubectl logs <pod>` |
| Describe resource | `kubectl describe <resource>` |
| Apply YAML | `kubectl apply -f file.yaml` |
| Delete resource | `kubectl delete -f file.yaml` |
| Enter container | `kubectl exec -it <pod> -- sh` |
| View events | `kubectl get events` |
| Check CPU/Memory | `kubectl top pods` |