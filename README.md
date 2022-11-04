# GKE-LabelForward
==

this is a simple services to apply GKE node label to compute engine label. 
where in current situation (Q3 2022), GKE nodepool label is not brought to billing. only compute engine label forwarded to billing.

this will benefit for user who wants to group/filter billing by nodepool label. ie:

|    Pool    |    Team   |
|------------|-----------|
| nodepool-1 | commerce  |
| nodepool-2 | logistic  |
| nodepool-3 | analytics |

there will be 2 activities that will be done with this :
1. get its kubernetes label for the node itself (samples below). 
```
{
	'app': 'app2',
	'beta.kubernetes.io/arch': 'amd64',
	'beta.kubernetes.io/instance-type': 'e2-medium',
	'beta.kubernetes.io/os': 'linux',
	'cloud.google.com/gke-boot-disk': 'pd-standard',
	'cloud.google.com/gke-container-runtime': 'containerd',
	'cloud.google.com/gke-cpu-scaling-level': '2',
	'cloud.google.com/gke-max-pods-per-node': '110',
	'cloud.google.com/gke-netd-ready': 'true',
	'cloud.google.com/gke-nodepool': 'pool-2',
	'cloud.google.com/gke-os-distribution': 'cos',
	'cloud.google.com/gke-spot': 'true',
	'cloud.google.com/machine-family': 'e2',
	'cloud.google.com/private-node': 'false',
	'failure-domain.beta.kubernetes.io/region': 'asia-southeast1',
	'failure-domain.beta.kubernetes.io/zone': 'asia-southeast1-c',
	'kubernetes.io/arch': 'amd64',
	'kubernetes.io/hostname': 'gke-cluster-1-pool-2-4005cfe7-wnlc',
	'kubernetes.io/os': 'linux',
	'node.kubernetes.io/instance-type': 'e2-medium',
	'pool': 'nganu2',
	'topology.gke.io/zone': 'asia-southeast1-c',
	'topology.kubernetes.io/region': 'asia-southeast1',
	'topology.kubernetes.io/zone': 'asia-southeast1-c'
}
```

it will pick up `topology.kubernetes.io/zone` value by default, which will be used for 2nd activities.
if `topology.kubernetes.io/zone` used by your organization, then please use `failure-domain.beta.kubernetes.io/zone` by specifying it in the daemonset.yaml `env` by utilizing `ZONE_LABEL` key

2. applied the `topology.kubernetes.io/zone` value from 1st activities to the same node as compute engine. wait for some times for label to be populated in billing


# Requirements

## 1. create role and service account in google cloud
this will be used for authorize. once created, export the key as json file. please be sure to use role that has :
    - compute.instances.setLabels
    - compute.instances.get

you may choose gcloud or via console. samples given via [GCLOUD](https://cloud.google.com/sdk/gcloud)

### Create Role
```
Create Role
gcloud iam roles create ROLE_NAME \
    --project=my-project-id --title="ROLE_TITLE" \
    --description="MY_DESCRIPTION" \
    --permissions="compute.instances.setLabels,compute.instances.get" --stage=GA
```

### Create Serviceaccount
```
Create Serviceaccount
gcloud iam service-accounts create SA_NAME \
    --description="DESCRIPTION" \
    --display-name="DISPLAY_NAME"
```

### Binding Service to IAM Role
```
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
    --role="ROLE_NAME"
```

```
Create json key for serviceaccount
gcloud iam service-accounts keys create KEY_FILE \
    --iam-account=SA_NAME@PROJECT_ID.iam.gserviceaccount.com
```

save your `json key` file.

for more information in :
  - serviceaccount creation, see [here](https://cloud.google.com/iam/docs/creating-managing-service-accounts)
  - serviceaccount create json key, see [here](https://cloud.google.com/iam/docs/creating-managing-service-account-keys)

2. import json keys as kubernetes secrets
```
kubectl create secret generic label-vol --from-file=key.json=/path/to/file/key.json
```

3. apply rbac.yaml in manifest folder
```
kubectl apply -f manifest/rbac.yaml
```

4. apply serviceaccount.yaml in manifest folder
```
kubectl apply -f manifest/serviceaccount.yaml
```

5. apply daemonset.yaml
```
kubectl apply -f daemonset.yaml
```


# Notes :
- this will not be working if you have nodepool that use taint/affinity/anti-affinity. 
for the workaround, please add toleration and adjust the daemonset.yaml accordingly, then redeploy the daemonset with different name.
