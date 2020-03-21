"""
Functionality for interacting with Kubernetes
"""
import kubernetes  # type: ignore
import structlog  # type: ignore

AWS_AUTH_NAMESPACE = "kube-system"

_LOG = structlog.get_logger()


def update_aws_auth_configmap(
    client: kubernetes.client.ApiClient, body: kubernetes.client.V1ConfigMap
) -> None:
    """
    Update the AWS auth ConfigMap in Kubernetes.
    If the ConfigMap doesn't exist, it's first created.

    :param client: Kubernetes client to use
    :param body: The new aws-auth ConfigMap
    """
    v1_api = kubernetes.client.CoreV1Api(client)
    name = body.metadata["name"]

    try:
        _LOG.debug("checking aws-auth configmap already exists")
        _ = v1_api.read_namespaced_config_map(name=name, namespace=AWS_AUTH_NAMESPACE)
        _LOG.debug("replacing existing aws-auth configmap")
        v1_api.replace_namespaced_config_map(
            name=name, namespace=AWS_AUTH_NAMESPACE, body=body
        )
    except kubernetes.client.rest.ApiException as err:
        if err.status == 404:
            _LOG.debug("creating new aws-auth configmap")
            v1_api.create_namespaced_config_map(namespace=AWS_AUTH_NAMESPACE, body=body)
        else:
            raise
