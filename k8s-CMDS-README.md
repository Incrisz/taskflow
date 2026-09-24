kubectl get pods

kubectl get po

kubectl get pods -o wide

kubectl get pods --show-labels

kubectl get pods -l "role=vote,version=v1"

kubectl get pods vote


kubectl logs vote

kubectl exec -it vote -- sh
