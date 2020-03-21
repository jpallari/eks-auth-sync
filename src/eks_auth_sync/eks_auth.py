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

# =========================
# Code copied from AWS CLI:
# https://github.com/aws/aws-cli/blob/eb3a253b2830f5e13046aa2ef996bddc2d8e2ed9/awscli/customizations/eks/get_token.py
#
# Changes made:
# * Removed the `GetTokenCommand` class, and the unused code.
# * Removed the region parameter.
# * Added `get_token` function which uses the rest of the code.
# * Made `TokenGenerator` private.
# * Replaced `STSClientFactory` with a function.
# * Replaced the session parameter with a `boto3.Session`
#
# =========================
"""
IAM authentication for EKS clusters.
"""

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
    """
    Fetch the authentication token for an EKS cluster.

    :param session: Boto3 session to use as a context for interacting with AWS
    :param cluster: Name of the EKS cluster
    :param role_arn: Optional IAM role ARN to assume as for the authentication
    :returns: A session token that can be used as a bearer token with the EKS cluster
    """
    sts_client = _create_sts_client(session, role_arn)
    token_gen = _TokenGenerator(sts_client)
    return token_gen.get_token(cluster)


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


def _create_sts_client(session: boto3.Session, role_arn: typing.Optional[str]):
    client_kwargs = {}
    if role_arn is not None:
        sts = session.client("sts")
        creds = sts.assume_role(RoleArn=role_arn, RoleSessionName="EKSGetTokenAuth")[
            "Credentials"
        ]
        client_kwargs["aws_access_key_id"] = creds["AccessKeyId"]
        client_kwargs["aws_secret_access_key"] = creds["SecretAccessKey"]
        client_kwargs["aws_session_token"] = creds["SessionToken"]
    sts = session.client("sts", **client_kwargs)
    _register_cluster_name_handlers(sts)
    return sts


def _register_cluster_name_handlers(sts_client):
    sts_client.meta.events.register(
        "provide-client-params.sts.GetCallerIdentity", _retrieve_cluster_name
    )
    sts_client.meta.events.register(
        "before-sign.sts.GetCallerIdentity", _inject_cluster_name_header
    )


def _retrieve_cluster_name(self, params, context, **kwargs):
    if "ClusterName" in params:
        context["eks_cluster"] = params.pop("ClusterName")


def _inject_cluster_name_header(self, request, **kwargs):
    if "eks_cluster" in request.context:
        request.headers[CLUSTER_NAME_HEADER] = request.context["eks_cluster"]
