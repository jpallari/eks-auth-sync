# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import typing
import base64
import boto3  # type: ignore

# Presigned url timeout in seconds
URL_TIMEOUT = 60

TOKEN_PREFIX = "k8s-aws-v1."

CLUSTER_NAME_HEADER = "x-k8s-aws-id"


def get_token(
    session: boto3.Session, cluster: str, role_arn: typing.Optional[str],
) -> str:
    client_factory = _STSClientFactory(session)
    sts_client = client_factory.get_sts_client(role_arn=role_arn)
    return _TokenGenerator(sts_client).get_token(cluster)


class _TokenGenerator:
    def __init__(self, sts_client):
        self._sts_client = sts_client

    def get_token(self, cluster_name):
        """ Generate a presigned url token to pass to kubectl. """
        url = self._get_presigned_url(cluster_name)
        token = TOKEN_PREFIX + base64.urlsafe_b64encode(url.encode("utf-8")).decode(
            "utf-8"
        ).rstrip("=")
        return token

    def _get_presigned_url(self, cluster_name):
        return self._sts_client.generate_presigned_url(
            "get_caller_identity",
            Params={"ClusterName": cluster_name},
            ExpiresIn=URL_TIMEOUT,
            HttpMethod="GET",
        )


class _STSClientFactory:
    def __init__(self, session):
        self._session = session

    def get_sts_client(self, role_arn=None):
        client_kwargs = {}
        if role_arn is not None:
            creds = self._get_role_credentials(role_arn)
            client_kwargs["aws_access_key_id"] = creds["AccessKeyId"]
            client_kwargs["aws_secret_access_key"] = creds["SecretAccessKey"]
            client_kwargs["aws_session_token"] = creds["SessionToken"]
        sts = self._session.client("sts", **client_kwargs)
        self._register_cluster_name_handlers(sts)
        return sts

    def _get_role_credentials(self, role_arn):
        sts = self._session.client("sts")
        return sts.assume_role(RoleArn=role_arn, RoleSessionName="EKSGetTokenAuth")[
            "Credentials"
        ]

    def _register_cluster_name_handlers(self, sts_client):
        sts_client.meta.events.register(
            "provide-client-params.sts.GetCallerIdentity", self._retrieve_cluster_name
        )
        sts_client.meta.events.register(
            "before-sign.sts.GetCallerIdentity", self._inject_cluster_name_header
        )

    def _retrieve_cluster_name(self, params, context, **kwargs):
        if "ClusterName" in params:
            context["eks_cluster"] = params.pop("ClusterName")

    def _inject_cluster_name_header(self, request, **kwargs):
        if "eks_cluster" in request.context:
            request.headers[CLUSTER_NAME_HEADER] = request.context["eks_cluster"]
