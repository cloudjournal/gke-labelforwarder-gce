from http import HTTPStatus
import json
import os
import time
import requests
import google.auth
import googleapiclient.discovery

ZONE_LABEL = os.getenv("ZONE_LABEL","topology.kubernetes.io/zone")
key_labels = os.getenv("KEY_LABELS")
check_interval = os.getenv("CHECK_INTERVAL","86400")
override_existing = os.getenv("OVERRIDE_LABELS", False)
logmessages = {}

def logprint(message, severity):
    logmessages["message"] = message
    logmessages["timestamp"] = time.time()
    logmessages["severity"] = severity
    print(json.dumps(logmessages))


def get_node_data(node_name, node_label_names):
    try:
        with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as file:
            auth_token = file.read()
    except OSError:
        logprint('Failed reading /var/run/secrets/kubernetes.io/serviceaccount/token', 'ERROR')
        exit(1)
    except IOError:
        logprint('Failed to read token', 'ERROR')
        exit(1)
    
    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') == "" :
        logprint('GOOGLE_APPLICATION_CREDENTIALS is required', 'ERROR')
        exit(1)

    resp = requests.get(url='https://kubernetes.default.svc/api/v1/nodes/' + node_name,
                        headers={'Authorization': 'Bearer ' + auth_token}, verify=False)
    if resp.status_code != HTTPStatus.OK:
        logprint('Failed to read data from ''{node}'' (status: {status})'.format(node=node_name, status=resp.status_code), 'ERROR')
    info = resp.json()
    labels = {}
    # print(info['metadata']['labels'])
    for key, value in info['metadata']['labels'].items():
        if key == ZONE_LABEL:
            zone = value
        if key in node_label_names:
            labels[key] = value
    return labels, zone


def update_vm_labels(instance_name, zone, labels):
    resp = ""
    creds, project_id = google.auth.default(
        scopes=['https://www.googleapis.com/auth/compute'])
    compute = googleapiclient.discovery.build(
        'compute', 'v1', credentials=creds)
    resp = compute.instances().get(project=project_id, zone=zone,
                                   instance=instance_name).execute()
    if 'error' in resp:
        logprint('Failed to get GCE instance info', 'ERROR')
        exit(1)
    fingerprint = resp['labelFingerprint']
    # prevent overriding existing labels
    if override_existing == "false":
        logprint('Not Overriding Labels', 'INFO')
        for key, value in resp['labels'].items():
            labels[key] = value
        logprint('applying labels {} to node {}'.format(labels, instance_name), 'INFO')
        resp = compute.instances().setLabels(project=project_id, zone=zone, instance=instance_name, body={
            'labelFingerprint': fingerprint,
            'labels': labels}).execute()
    # overriding existing labels
    elif override_existing == "true":
        logprint('Overriding Labels', 'INFO')
        original_labels = resp['labels']
        for key, value in labels.items():
            original_labels[key] = value
        logprint('applying labels {} to node {}'.format(labels, instance_name), 'INFO')
        resp = compute.instances().setLabels(project=project_id, zone=zone, instance=instance_name, body={
            'labelFingerprint': fingerprint,
            'labels': original_labels}).execute()
    else:
        logprint('OVERRIDE_LABELS missing', 'ERROR')
        exit(1)
    if 'error' in resp:
        logprint('Failed to set Cloud labels for ''{node}''\n'.format(node=instance_name), 'ERROR')
        for err in resp['error']['errors']:
            logprint('code: {code} / location: {location} / msg: {msg}\n'.format(code=err['code'], location=err['location'], msg=err['message']), 'ERROR')
        exit(1)


def main():
    if key_labels == None:
        logprint('Environment KEY_LABELS cannot be empty', 'ERROR')
        exit(1)
    node_name = os.getenv('NODE_NAME')
    if node_name == '':
        logprint('Environment variable NODE_NAME is not defined', 'ERROR')
        exit(1)
    while(True):
        node_labels, zone = get_node_data(node_name, key_labels)
        # logprint('node label was {}'.format(node_labels), 'INFO')
        update_vm_labels(node_name, zone, node_labels)
        logprint('success update kubernetes labels to compute engine label {}'.format(node_labels), 'INFO')
        time.sleep(int(check_interval))

if __name__ == '__main__':
    main()