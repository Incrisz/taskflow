# TaskFlow — Configuration, Helm, Administration, Observability and Security

This guide continues `02-README.md` and covers:

- **Module 5:** ConfigMaps, Secrets and Helm charts.
- **Module 6:** Cluster administration and RBAC.
- **Module 7:** Monitoring, logging and Pod troubleshooting.
- **Module 8:** Production practices, security hardening and recovery.

The files are executable learning examples. The monitoring stack uses single replicas and ephemeral storage to keep the lab small; it is not a highly available production installation. No external alert notifications are configured.

## 1. Prerequisites and file order

Run commands from the repository root. You need a working Kubernetes context, `kubectl`, Helm, access to the application images, and a default StorageClass (or suitable pre-provisioned volumes). The backup CronJob uses `timeZone`, requiring Kubernetes 1.27 or newer. Use a supported Kubernetes release for your environment.

```bash
kubectl config current-context
kubectl cluster-info
kubectl get nodes
kubectl get storageclass
helm version
```

Use a disposable training cluster for failure and node-maintenance exercises. Allow additional CPU and memory for Prometheus, Grafana, Alertmanager, Loki and Alloy; each has explicit resource requests and limits. Their namespace is separate from the application quota.

| Order | Location | What it provides |
| --- | --- | --- |
| 00–06 | Existing numbered `kubernetes/` files | Application, configuration, database and Redis |
| Module 5 alternative | `helm/taskflow/` | Helm packaging in a separate namespace |
| 07 | `kubernetes/07-administration/` | Reader permissions, node visibility, quota and defaults |
| 08 | `kubernetes/08-monitoring/` | Prometheus, Alertmanager and provisioned Grafana dashboard |
| 09 | `kubernetes/09-logging/` | Loki and Alloy log collection |
| 10 | `overlays/10-production/` | Kustomize overlay for the existing application |
| 11 | `kubernetes/11-backups/` | Backup storage, CronJob and restore helper Pod |

The overlay lives outside `kubernetes/` so Kustomize can reference the application base without a recursive directory reference. Never recursively apply the whole repository: Helm templates, Kustomize patches and optional resources have different workflows.

For a fresh application installation, follow `02-README.md`, or apply the equivalent base:

```bash
kubectl apply -k kubernetes/
kubectl -n taskflow rollout status statefulset/postgres --timeout=180s
kubectl -n taskflow rollout status deployment/redis --timeout=180s
kubectl -n taskflow rollout status deployment/taskflow-api --timeout=180s
kubectl -n taskflow rollout status deployment/taskflow-frontend --timeout=180s
kubectl -n taskflow get pods,svc,pvc
```

The API manifest specifies UID/GID 1000 to match the Node image: `runAsNonRoot` alone cannot verify a Docker image configured with the username `node` instead of a numeric UID.

The base includes teaching credentials from Module 3. The production overlay excludes that Secret so applying it does not reset separately managed credentials.

### Database initialization

`kubernetes/03-postgres/init-configmap.yaml` mounts the schema and seed data from `database/init.sql` into PostgreSQL's initialization directory. The SQL runs automatically only when PostgreSQL initializes an **empty** data directory. Helm includes the same SQL.

For an existing lab database that is missing the tasks table, initialize it explicitly:

```bash
kubectl -n taskflow exec -i postgres-0 -- sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  < database/init.sql
```

The supplied SQL creates the table if missing and seeds it only when empty. It is not a general schema migration system. If you change this SQL later, update both initialization ConfigMaps as well.

## 2. Module 5 — ConfigMaps and Secrets

### Inspect the configuration flow

```text
ConfigMap taskflow-config ──┐
                           ├── API environment
Secret taskflow-secret ─────┘
          │
          └── PostgreSQL credentials

Frontend API_URL=http://api:5000/api → nginx → API Service
```

Read the configuration without printing Secret values:

```bash
kubectl -n taskflow get configmap taskflow-config -o yaml
kubectl -n taskflow describe secret taskflow-secret
kubectl -n taskflow describe deployment taskflow-api
```

ConfigMaps hold non-sensitive settings. Secret values are not made confidential merely by base64 encoding; protect their API access, configure cluster encryption at rest where appropriate, and use your platform's secret manager for production delivery. The checked-in password is for this lab only.

### Update configuration and restart consumers

A ConfigMap or Secret injected as environment variables is read when a container starts. Updating the object does not rewrite the running process environment.

This exercise adds a harmless marker and confirms the restart behavior:

```bash
kubectl -n taskflow patch configmap taskflow-config --type merge \
  -p '{"data":{"LAB_MODULE":"5"}}'
kubectl -n taskflow rollout restart deployment/taskflow-api
kubectl -n taskflow rollout status deployment/taskflow-api
kubectl -n taskflow exec deployment/taskflow-api -- printenv LAB_MODULE
```

Expected output: `5`. The application does not otherwise use this marker. For a permanent configuration change, edit the source manifest or Helm values too.

### Create independently managed credentials

The Helm exercise below creates `taskflow-secret` in a new namespace. In a production setup, supply this Secret through your secret management process; do not copy the example password into a real environment.

Changing `POSTGRES_PASSWORD` in a Secret **does not change the password of an existing PostgreSQL database role**. For an existing database, coordinate a database-side password change (`psql`'s interactive `\password taskflow`, for example), update the Secret, and restart API consumers in a maintenance window. Do not delete the database PVC to rotate credentials. A single-role rotation can temporarily interrupt connections.

## 3. Module 5 — Helm chart

A chart packages Kubernetes templates; `values.yaml` supplies the configurable inputs. This chart exposes application images and replicas, PostgreSQL storage/image, Redis image, database name and the existing Secret name. It retains the same Service names and labels as the earlier exercises.

**Use one release per namespace.** The chart intentionally uses fixed resource names. Install into `taskflow-helm`, not the existing `taskflow` namespace; otherwise Helm will encounter resources owned by the manual deployment. This is an independent demo with its own database, not a migration of the existing data.

### Validate and render

```bash
helm lint helm/taskflow
helm template taskflow helm/taskflow --namespace taskflow-helm
```

### Install

Create the namespace and credentials first. This Bash example reads the password without echoing it or embedding it in shell history:

```bash
kubectl create namespace taskflow-helm --dry-run=client -o yaml | kubectl apply -f -
read -r -s -p 'New lab database password: ' taskflow_password
printf '\n'
{
  printf 'DB_USER=taskflow\n'
  printf 'DB_PASSWORD=%s\n' "$taskflow_password"
} | kubectl -n taskflow-helm create secret generic taskflow-secret \
  --from-env-file=/dev/stdin --dry-run=client -o yaml | kubectl apply -f -
unset taskflow_password

helm upgrade --install taskflow helm/taskflow \
  --namespace taskflow-helm --wait --timeout 5m
kubectl -n taskflow-helm get pods,svc,pvc
kubectl -n taskflow-helm port-forward service/frontend 3001:80
```

Visit `http://localhost:3001` and create a task. The frontend keeps `/api/` requests on the same browser origin and proxies them to `api:5000` inside its namespace. If registry images cannot be pulled, build/load local images and override `api.image` and `frontend.image` in Helm values.

### Upgrade, inspect and roll back

```bash
helm upgrade taskflow helm/taskflow --namespace taskflow-helm \
  --set api.replicas=3 --wait --timeout 5m
helm history taskflow --namespace taskflow-helm
helm get values taskflow --namespace taskflow-helm
helm rollback taskflow 1 --namespace taskflow-helm --wait --timeout 5m
```

Revision `1` assumes this was a fresh installation; choose the desired revision from history otherwise. Helm rollback restores Kubernetes configuration, not database contents. Do not change the database name or shrink a PVC as a routine upgrade of an existing installation. ConfigMap/Secret environment changes still need a rollout restart of their consumers.

The remaining modules target the original **`taskflow`** namespace. Monitoring, backups and the production overlay do not automatically manage the Helm demo.

## 4. Module 6 — RBAC and administration

### Namespaced and cluster-wide permissions

```bash
kubectl apply -f kubernetes/07-administration/01-reader-rbac.yaml
kubectl apply -f kubernetes/07-administration/02-node-reader.yaml
```

The `taskflow-reader` ServiceAccount can read application workloads and logs using a Role/RoleBinding. A separate ClusterRole/ClusterRoleBinding allows reading nodes because nodes are cluster-scoped. Neither grants access to Secrets or permission to modify workloads.

Test as a cluster administrator allowed to impersonate this account:

```bash
kubectl auth can-i list pods -n taskflow \
  --as=system:serviceaccount:taskflow:taskflow-reader
kubectl auth can-i get nodes \
  --as=system:serviceaccount:taskflow:taskflow-reader
kubectl auth can-i get secrets -n taskflow \
  --as=system:serviceaccount:taskflow:taskflow-reader
kubectl auth can-i delete deployments -n taskflow \
  --as=system:serviceaccount:taskflow:taskflow-reader
```

Expected results: `yes`, `yes`, `no`, `no`. An impersonation error means your current account lacks permission to perform this test; it does not describe the reader account's permissions.

The original API ServiceAccount's read permissions were for teaching. The application itself does not call the Kubernetes API; Module 8 disables token mounting and removes its old RoleBinding.

### Quotas and resource defaults

```bash
kubectl apply -f kubernetes/07-administration/03-limits.yaml
kubectl -n taskflow describe limitrange taskflow-defaults
kubectl -n taskflow describe resourcequota taskflow-quota
```

LimitRange supplies requests/limits to newly created containers that omit them. Existing Pods are not retroactively changed. ResourceQuota bounds namespace-wide resources, including Pods and storage. A quota can reject new replicas or rollout surge Pods; inspect events when a Deployment does not progress. These are training values, so size them against actual capacity before adopting them.

### Contexts and node maintenance

```bash
kubectl config get-contexts
kubectl config current-context
kubectl get nodes -o wide
kubectl describe node <worker-node>
kubectl get pods -A -o wide --field-selector spec.nodeName=<worker-node>
```

On a disposable multi-node cluster, after checking spare capacity and storage mobility:

```bash
kubectl cordon <worker-node>
kubectl drain <worker-node> --ignore-daemonsets --delete-emptydir-data
# Perform maintenance, then allow scheduling again:
kubectl uncordon <worker-node>
```

`cordon` prevents new scheduling. `drain` requests eviction and respects PodDisruptionBudgets. The command explicitly discards `emptyDir` data: this includes this lab's monitoring history and Redis cache. Do not force a blocked drain; inspect disruption budgets, local storage and capacity first. Local PostgreSQL volumes may tie the database to a particular node. A single-node cluster cannot demonstrate uninterrupted service during maintenance.

Control-plane upgrades and etcd snapshots depend on whether your cluster is managed, kubeadm-based or another distribution. Follow that distribution's runbook. PostgreSQL backups in Module 8 are application data backups, not cluster-state backups.

## 5. Module 7 — Monitoring and alerting

### Install the monitoring stack

Create the namespace first, then the required Grafana admin Secret:

```bash
kubectl apply -f kubernetes/08-monitoring/00-namespace.yaml
read -r -s -p 'Grafana admin password: ' grafana_password
printf '\n'
printf 'password=%s\n' "$grafana_password" | \
  kubectl -n monitoring create secret generic grafana-admin \
  --from-env-file=/dev/stdin --dry-run=client -o yaml | kubectl apply -f -
unset grafana_password

kubectl apply -f kubernetes/08-monitoring/01-rbac.yaml
kubectl apply -f kubernetes/08-monitoring/02-prometheus.yaml
kubectl apply -f kubernetes/08-monitoring/03-alertmanager.yaml
kubectl apply -f kubernetes/08-monitoring/04-grafana.yaml
kubectl -n monitoring rollout status deployment/prometheus --timeout=180s
kubectl -n monitoring rollout status deployment/alertmanager --timeout=180s
kubectl -n monitoring rollout status deployment/grafana --timeout=180s
```

Prometheus discovers each API Pod in `taskflow` and scrapes port 5000 at `/metrics`. Its Role permits Pod discovery only in that namespace. This avoids collecting metrics from just one replica behind a Service. It does not install kube-state-metrics or a node exporter; cluster infrastructure metrics are outside this small stack.

In separate terminals:

```bash
kubectl -n monitoring port-forward service/prometheus 9090:9090
kubectl -n monitoring port-forward service/grafana 3002:3000
kubectl -n monitoring port-forward service/alertmanager 9093:9093
```

Open Prometheus at `http://localhost:9090`, Grafana at `http://localhost:3002` (user `admin`, password entered above), and Alertmanager at `http://localhost:9093`.

Grafana provisions Prometheus and Loki data sources and a **TaskFlow** dashboard with request rate, HTTP 5xx rate, p95 duration and scrape health. Loki becomes available after the next section.

### Generate traffic and inspect metrics

Keep the application port forward running in another terminal:

```bash
kubectl -n taskflow port-forward service/frontend 3000:80
```

Then:

```bash
for request in $(seq 1 30); do
  curl --fail --silent http://localhost:3000/api/tasks > /dev/null
  sleep 1
done
```

Use these Prometheus queries:

```promql
up{job="taskflow-api"}
sum(rate(taskflow_http_requests_total[5m]))
histogram_quantile(0.95, sum by (le) (rate(taskflow_http_request_duration_seconds_bucket[5m])))
```

Allow a few scrape intervals for graphs to populate. Metrics include probe/scrape requests as instrumented by the current application; they are not exclusively end-user traffic.

### Alert exercise

Two rules are included: unavailable API scrape targets for two minutes, and an HTTP 5xx rate above 5% for five minutes. They are sent to Alertmanager's `lab` receiver. The receiver intentionally has no email/webhook destination; inspect alerts in the UI. Add your own protected notification integration before depending on this for operations.

Before enabling the HPA, record the current API replica count, scale to zero in the training cluster, wait about three minutes, inspect the unavailable-target alert, and restore the count:

```bash
api_replicas=$(kubectl -n taskflow get deployment taskflow-api -o jsonpath='{.spec.replicas}')
kubectl -n taskflow scale deployment/taskflow-api --replicas=0
# Inspect Prometheus /alerts and Alertmanager after the pending interval.
kubectl -n taskflow scale deployment/taskflow-api --replicas="$api_replicas"
kubectl -n taskflow rollout status deployment/taskflow-api
```

This deliberately interrupts the API. Scrape availability is not a complete readiness/SLO check: an API can expose metrics while its database is unavailable.

## 6. Module 7 — Centralized logging

```bash
kubectl apply -f kubernetes/09-logging/01-loki.yaml
kubectl apply -f kubernetes/09-logging/02-alloy.yaml
kubectl -n monitoring rollout status deployment/loki --timeout=180s
kubectl -n monitoring rollout status deployment/alloy --timeout=180s
kubectl -n monitoring logs deployment/alloy --tail=50
```

Alloy discovers Pods and tails their logs through the Kubernetes API using namespace-scoped permissions. It forwards entries to Loki; no host filesystem mounts are needed. In Grafana **Explore**, select Loki and run:

```logql
{namespace="taskflow"}
{namespace="taskflow", container="api"}
{namespace="taskflow", container="frontend"}
```

The API currently logs startup and errors, not a structured record for every request. Nginx access logs provide request activity. Centralized collection does not create application log events that were never emitted.

Loki, Prometheus, Grafana's local database and Alertmanager state use `emptyDir`; recreation loses their stored history/state. Provisioned dashboards return from ConfigMaps. Use persistent storage, retention policies, authentication and appropriately sized/available services before using this stack in production. Keep these unauthenticated internal monitoring endpoints behind ClusterIP and local port forwarding in the lab.

After editing an embedded configuration, apply its manifest and restart its Deployment to make reload behavior explicit:

```bash
kubectl apply -f kubernetes/08-monitoring/02-prometheus.yaml
kubectl -n monitoring rollout restart deployment/prometheus
kubectl -n monitoring rollout status deployment/prometheus
```

### Troubleshooting workflow

```bash
kubectl -n taskflow get pods -o wide
kubectl -n taskflow describe pod <pod-name>
kubectl -n taskflow logs <pod-name> --all-containers --tail=100
kubectl -n taskflow logs <pod-name> --previous
kubectl -n taskflow get events --sort-by=.metadata.creationTimestamp
kubectl -n taskflow get endpointslices -l kubernetes.io/service-name=api
kubectl -n taskflow get pvc
```

| Symptom | Check |
| --- | --- |
| `Pending` | Requests, quota, node capacity, PVC binding and storage topology |
| `ImagePullBackOff` | Image name, tag, registry credentials or local image loading |
| `CreateContainerConfigError` | Referenced ConfigMap/Secret names and required keys |
| `CrashLoopBackOff` | Current/previous logs, command, writable paths and probes |
| API running but not ready | PostgreSQL/Redis connectivity, credentials and network policy |
| Tasks return errors while readiness passes | The tasks table exists; `/ready` checks connectivity, not schema |
| Empty Service EndpointSlices | Selector/label mismatch or Pods not ready |
| Empty Grafana graphs | Prometheus targets, time range, scrape permissions and generated traffic |
| Missing Loki logs | Alloy logs/RBAC, Loki availability and actual container output |

For another reversible failure exercise, set the API image to a nonexistent tag in the disposable cluster, inspect the Pod events, then undo:

```bash
kubectl -n taskflow set image deployment/taskflow-api api=incriszz/taskflow-api:does-not-exist
kubectl -n taskflow get pods
kubectl -n taskflow describe pod <new-failing-pod>
kubectl -n taskflow rollout undo deployment/taskflow-api
kubectl -n taskflow rollout status deployment/taskflow-api
```

## 7. Module 8 — Hardening the application

### Review and apply the overlay

Prerequisites: the existing application Secret/database, a CNI that enforces NetworkPolicy, and knowledge of your cluster's DNS labels. The supplied DNS rule assumes CoreDNS Pods in `kube-system` labeled `k8s-app=kube-dns`. Adapt it for NodeLocal DNS or other installations before applying default-deny egress.

```bash
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl kustomize overlays/10-production
kubectl diff -k overlays/10-production
kubectl apply -k overlays/10-production
# Omission from Kustomize output does not delete an already-live object:
kubectl -n taskflow delete rolebinding taskflow-readonly --ignore-not-found
kubectl -n taskflow rollout status deployment/taskflow-api --timeout=180s
kubectl -n taskflow rollout status deployment/taskflow-frontend --timeout=180s
kubectl -n taskflow rollout status statefulset/postgres --timeout=180s
kubectl -n taskflow rollout status deployment/redis --timeout=180s
```

`kubectl diff` returns exit code 1 when differences exist. Review those differences; it does not apply them.

The overlay:

- Disables application ServiceAccount token mounts and removes the API's teaching RoleBinding from rendered output.
- Uses explicit non-root identities, `RuntimeDefault` seccomp, no privilege escalation and dropped capabilities.
- Uses read-only root filesystems for API, frontend and Redis. PostgreSQL retains a writable root filesystem and uses its persistent data volume plus a writable socket directory.
- Runs nginx on port 8080 with configuration and temporary files under `/tmp`; the frontend Service still exposes port 80 and preserves `API_URL` proxying.
- Adds frontend probes, API startup probing and dependency readiness checks.
- Adds resource limits to PostgreSQL and Redis, preferred API replica separation, and disruption budgets for API/frontend.
- Applies default-deny ingress/egress, then allows DNS, frontend → API, API → database/cache, Prometheus → API, backup → PostgreSQL, and ingress-controller → frontend.

The PostgreSQL identity is UID/GID 70 for the pinned Alpine image. Check ownership and storage-driver `fsGroup` support before applying this to an existing volume. Do not use this patch unchanged with an image that has a different database UID.

The ingress allow rule assumes the controller runs in `ingress-nginx`; edit it if yours runs elsewhere. NetworkPolicy enforcement depends on the CNI and is not guaranteed just because the API accepts the objects. Namespace RBAC must also prevent untrusted users from creating Pods with trusted labels.

The namespace enforces the **baseline** Pod Security standard while auditing/warning against **restricted**. After checking every workload (including maintenance/debug jobs), you can explicitly enable restricted enforcement:

```bash
kubectl label namespace taskflow pod-security.kubernetes.io/enforce=restricted --overwrite
```

Make that change in `overlays/10-production/patches/namespace.yaml` too if you want it preserved on later applies. Policies here are learning settings; evaluate version-pinned policy levels for your supported cluster version.

Do not reapply the base or `02-rbac/` after hardening without reviewing the effects: that can restore teaching credentials/permissions, root nginx behavior and fixed replica counts. The overlay is now the source of truth for this deployment.

### Verify hardening and connectivity

```bash
kubectl -n taskflow get networkpolicy,pdb
kubectl -n taskflow exec deployment/taskflow-api -- id
kubectl -n taskflow exec deployment/taskflow-frontend -- id
kubectl -n taskflow get deployment taskflow-api \
  -o jsonpath='{.spec.template.spec.automountServiceAccountToken}'
kubectl auth can-i list pods -n taskflow \
  --as=system:serviceaccount:taskflow:taskflow-api
```

Expected: non-root identities, `false`, and `no` (assuming no additional bindings grant this account permissions). Restart any old frontend port-forward after the port change, then test task creation/listing through the UI and confirm Prometheus still has targets and Alloy still has logs.

Test policy enforcement with the supplied restricted-compatible diagnostic Pod:

```bash
kubectl apply -f overlays/10-production/verification/network-test.yaml
kubectl -n taskflow wait --for=condition=Ready pod/network-test --timeout=120s
kubectl -n taskflow exec network-test -- nslookup api
# Expected: connection timeout/nonzero exit; DNS above should still succeed.
kubectl -n taskflow exec network-test -- wget -T 3 -qO- http://api:5000/health
# Expected: healthy JSON from the permitted frontend workload.
kubectl -n taskflow exec deployment/taskflow-frontend -- wget -T 3 -qO- http://api:5000/health
kubectl -n taskflow delete pod network-test
```

A DNS failure or a missing API is not evidence of correct policy enforcement; confirm the allowed request succeeds. Test this on your CNI before claiming isolation.

### Autoscaling

Install Metrics Server using the instructions for your cluster distribution. Confirm it works before applying the HPA:

```bash
kubectl top nodes
kubectl -n taskflow top pods
kubectl apply -f overlays/10-production/optional/hpa.yaml
kubectl -n taskflow get hpa
kubectl -n taskflow describe hpa taskflow-api
```

The HPA targets average API CPU utilization of 60% of its request and scales between two and six replicas. Prometheus is separate from the Metrics Server resource-metrics pipeline. If targets show `<unknown>`, investigate Metrics Server and CPU requests. Avoid manual scaling or repeated applies that reset `spec.replicas` while the HPA is active. For a long-lived HPA-managed deployment, remove fixed replicas from its declarative source.

### TLS ingress

An Ingress object needs a working controller. The sample uses an existing controller with class `nginx`; it does not install one. Adapt both `ingressClassName` and the frontend NetworkPolicy for your supported controller. Set the hostname in the manifest to a domain you control for a real deployment.

For a local `taskflow.local` exercise, create a short-lived self-signed certificate:

```bash
openssl req -x509 -nodes -newkey rsa:2048 -days 7 \
  -keyout /tmp/taskflow-tls.key -out /tmp/taskflow-tls.crt \
  -subj '/CN=taskflow.local' -addext 'subjectAltName=DNS:taskflow.local'
kubectl -n taskflow create secret tls taskflow-tls \
  --cert=/tmp/taskflow-tls.crt --key=/tmp/taskflow-tls.key \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f overlays/10-production/optional/ingress.yaml
kubectl -n taskflow get ingress
```

Map `taskflow.local` to the reachable ingress address using local DNS/hosts. Use the generated certificate as a trust anchor for a command-line test:

```bash
curl --cacert /tmp/taskflow-tls.crt https://taskflow.local/api/tasks
```

Use trusted certificates and automated renewal for real deployments. Do not expose the current TaskFlow app publicly as a secure multi-user service: it has no user authentication/authorization, and Kubernetes hardening does not add those application controls.

### Production release checks

The image tags in these examples are fixed lab inputs, not a claim that those versions have passed a current vulnerability review. Before promotion, scan application and third-party images, select supported patched releases, pin approved image digests, and test the complete task flow in staging. Size requests/limits from observed load, verify graceful shutdown during rolling updates, and confirm spare capacity for disruption budgets and surge replicas.

Keep database credentials outside source control, use a dedicated database role with only the permissions the application needs, and verify encrypted off-cluster backups. This lab reuses PostgreSQL's bootstrap role for simplicity. A single database replica and local PVC are not a highly available database design.

## 8. Module 8 — Backups and recovery

```bash
kubectl apply -f kubernetes/11-backups/01-storage.yaml
kubectl apply -f kubernetes/11-backups/02-cronjob.yaml
kubectl -n taskflow get cronjob,pvc
```

The CronJob runs daily at 02:00 UTC, creates a PostgreSQL custom-format dump, checks that its archive listing is readable, and keeps about seven days of successful dump files. It reads credentials from the existing Secret. This is logical database backup, not PostgreSQL physical backup or point-in-time recovery. Size the 5Gi backup volume for your data and retention.

Run and inspect an immediate backup:

```bash
backup_job="postgres-backup-manual-$(date +%s)"
kubectl -n taskflow create job --from=cronjob/postgres-backup "$backup_job"
kubectl -n taskflow wait --for=condition=complete "job/$backup_job" --timeout=300s
kubectl -n taskflow logs "job/$backup_job"
```

### Download and restore into a separate verification database

The backup PVC is ReadWriteOnce. Suspend future scheduled Jobs and wait for any current backup to finish before mounting it with the reader Pod, especially on multi-node clusters. Suspending a CronJob does not stop an active Job.

```bash
kubectl -n taskflow patch cronjob postgres-backup --type merge -p '{"spec":{"suspend":true}}'
kubectl -n taskflow get jobs
kubectl apply -f kubernetes/11-backups/restore/reader.yaml
kubectl -n taskflow wait --for=condition=Ready pod/backup-reader --timeout=180s
kubectl -n taskflow exec backup-reader -- ls -lh /backups
```

Choose a completed `.dump` filename from that listing, then download it (replace the example timestamp):

```bash
umask 077
kubectl -n taskflow exec backup-reader -- \
  cat /backups/taskflow-20260924T020000Z.dump > /tmp/taskflow-restore.dump
bash scripts/restore-postgres.sh /tmp/taskflow-restore.dump
```

The script creates a new `taskflow_restore_<timestamp>` database, restores with errors treated as failures, and counts restored tasks. It refuses arbitrary target names and fails if the target already exists. It does not overwrite the active `taskflow` database. An incomplete restore may leave the verification database behind; inspect it before manually removing it or choose a new verification name.

After verification:

```bash
kubectl -n taskflow delete pod backup-reader
kubectl -n taskflow patch cronjob postgres-backup --type merge -p '{"spec":{"suspend":false}}'
```

Record restore duration and validate representative records, not only the archive listing. Store encrypted backup copies outside the cluster with access controls and a tested recovery runbook. A backup PVC in the same cluster does not protect against losing that cluster/storage system.

## 9. Validation and completion checklist

Local rendering and static checks:

```bash
bash scripts/validate-kubernetes.sh
```

The helper needs Python 3 with PyYAML, Helm and kubectl. It performs no cluster mutations. With a configured test cluster, also validate against its actual APIs/admission rules before applying:

```bash
kubectl apply --dry-run=server -k kubernetes/
kubectl apply --dry-run=server -k overlays/10-production/
```

Namespaces and external prerequisites must already exist for meaningful server-side checks. Rendering is not proof that an image can start, a volume can bind, or a network policy is enforced.

You have completed the exercises when:

- ConfigMap changes appear after a rollout, and you can explain Secret/password rotation behavior.
- Helm install, upgrade and rollback work in the isolated demo namespace.
- RBAC allows the intended reads and denies Secrets and workload modifications.
- Prometheus scrapes every API Pod, Grafana shows traffic, and a deliberate failure produces an alert.
- Loki contains application container logs and you can investigate a failed Pod using events and previous logs.
- Hardened workloads run as non-root, task operations work, and policy tests allow/deny the expected traffic.
- HPA has valid metrics, TLS ingress works with your controller, and a backup restores into a separate database.

### Cleanup

Stop port forwards with Ctrl+C. For the separate Helm demo:

```bash
helm uninstall taskflow --namespace taskflow-helm
```

Its externally created Secret and PostgreSQL PVC remain. Deleting the namespace deletes those resources too, so only do that when its database is disposable.

To remove the optional lab observability and administration objects:

```bash
kubectl delete -f kubernetes/09-logging/
kubectl delete -f kubernetes/08-monitoring/04-grafana.yaml
kubectl delete -f kubernetes/08-monitoring/03-alertmanager.yaml
kubectl delete -f kubernetes/08-monitoring/02-prometheus.yaml
kubectl delete -f kubernetes/08-monitoring/01-rbac.yaml
kubectl delete -f kubernetes/07-administration/
```

Removing ephemeral monitoring workloads discards their history. The `monitoring` namespace and manually created Grafana Secret are left in place. Do not run `kubectl delete -k overlays/10-production` as an overlay rollback: its rendered resources include the application base. Preserve database and backup PVCs until their data is no longer needed.

## References

- [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/) and [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Helm values files](https://helm.sh/docs/chart_template_guide/values_files/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Prometheus configuration and Kubernetes discovery](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Alloy Kubernetes log source](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/)
- [Loki configuration examples](https://grafana.com/docs/loki/latest/configure/examples/configuration-examples/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Pod disruption budgets](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
