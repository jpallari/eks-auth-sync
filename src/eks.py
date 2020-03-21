import base64
import boto3  # type: ignore
import kubernetes  # type: ignore
import tempfile
import eks_auth
import typing


def api_config(
    session: boto3.Session, cluster: str, role_arn: typing.Optional[str],
) -> kubernetes.client.Configuration:
    eks_client = session.client("eks")
    eks_details = eks_client.describe_cluster(name=cluster)["cluster"]
    endpoint = eks_details["endpoint"]
    ca_data = eks_details["certificateAuthority"]["data"]

    conf = kubernetes.client.Configuration()
    conf.host = endpoint
    conf.api_key["authorization"] = eks_auth.get_token(
        session=session, cluster=cluster, role_arn=role_arn,
    )
    conf.api_key_prefix["authorization"] = "Bearer"
    conf.ssl_ca_cert = _save_eks_ca_cert(ca_data)
    return conf


def _save_eks_ca_cert(ca_cert_b64: str) -> str:
    fp = tempfile.NamedTemporaryFile(delete=False)
    cert_bs = base64.urlsafe_b64decode(ca_cert_b64.encode("utf-8"))
    fp.write(cert_bs)
    fp.close()
    return fp.name
