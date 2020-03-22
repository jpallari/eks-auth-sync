"""
EKS related functions excluding the authentication.
"""
import tempfile
import typing
import base64
import boto3  # type: ignore
import kubernetes  # type: ignore
from eks_auth_sync import _eks_auth


def api_config(
    session: boto3.Session, cluster: str, role_arn: typing.Optional[str],
) -> kubernetes.client.Configuration:
    """
    Create a Kubernetes client configuration for EKS.

    :param session: Boto3 session to use as a context for interacting with AWS
    :param cluster: Name of the EKS cluster
    :param role_arn: Optional IAM role ARN to assume as for the authentication
    :returns: A configuration object that can be used with the Kubernetes client to login to EKS.

    Note that this will write the cluster CA to a temporary file,
    because that's the only way it can be provided to the Kubernetes client.
    """
    eks_client = session.client("eks")
    eks_details = eks_client.describe_cluster(name=cluster)["cluster"]
    endpoint = eks_details["endpoint"]
    ca_data = eks_details["certificateAuthority"]["data"]

    conf = kubernetes.client.Configuration()
    conf.host = endpoint
    conf.api_key["authorization"] = _eks_auth.get_token(
        session=session, cluster=cluster, role_arn=role_arn,
    )
    conf.api_key_prefix["authorization"] = "Bearer"
    conf.ssl_ca_cert = _save_eks_ca_cert(ca_data)
    return conf


def _save_eks_ca_cert(ca_cert_b64: str) -> str:
    ca_cert_file = tempfile.NamedTemporaryFile(delete=False)
    cert_bs = base64.urlsafe_b64decode(ca_cert_b64.encode("utf-8"))
    ca_cert_file.write(cert_bs)
    ca_cert_file.close()
    return ca_cert_file.name
