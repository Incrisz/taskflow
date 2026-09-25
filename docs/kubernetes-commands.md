helm install taskflow . -n taskflow --create-namespace

or


kubectl create namespace taskflow


helm lint .

helm template taskflow .

helm install taskflow . -n taskflow

helm list -n taskflow

helm upgrade taskflow .

helm uninstall taskflow -n taskflow

helm install taskflow-prod . -n taskflow-prod -f values-staging.yaml

helm list -A