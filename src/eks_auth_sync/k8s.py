import kubernetes  # type: ignore
import structlog  # type: ignore

AWS_AUTH_NAMESPACE = "kube-system"

logger = structlog.get_logger()


def update_aws_auth_cm(
    client: kubernetes.client.ApiClient, body: kubernetes.client.V1ConfigMap
) -> None:
    v1 = kubernetes.client.CoreV1Api(client)
    name = body.metadata["name"]

    try:
        logger.debug("checking aws-auth configmap already exists")
        _ = v1.read_namespaced_config_map(name=name, namespace=AWS_AUTH_NAMESPACE)
        logger.debug("replacing existing aws-auth configmap")
        v1.replace_namespaced_config_map(
            name=name, namespace=AWS_AUTH_NAMESPACE, body=body
        )
    except kubernetes.client.rest.ApiException as e:
        if e.status == 404:
            logger.debug("creating new aws-auth configmap")
            v1.create_namespaced_config_map(namespace=AWS_AUTH_NAMESPACE, body=body)
        else:
            raise
