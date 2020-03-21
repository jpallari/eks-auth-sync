"""
Scanner is used for scanning AWS APIs for EKS cluster users.
"""
import typing
import boto3  # type: ignore
import structlog  # type: ignore
from eks_auth_sync.mapping import MappingType, Mapping

_LOG = structlog.get_logger()


class Scanner:
    """
    Scanner is used for scanning AWS APIs for EKS cluster users.

    :param session: Boto3 session to use as a context for interacting with AWS
    :param cluster: Name of the EKS cluster
    """

    def __init__(self, session: boto3.Session, cluster: str) -> None:
        self._session = session
        self._sts_client = session.client("sts")
        self._iam_client = session.client("iam")
        self._account_id_v = ""
        self._cluster = cluster
        self._logger = _LOG.new(cluster=cluster)

    @property
    def _account_id(self) -> str:
        if not self._account_id_v:
            self._account_id_v = self._sts_client.get_caller_identity()["Account"]
            self._logger.debug("found AWS account ID", account_id=self._account_id_v)
        return self._account_id_v

    def from_iam_roles(self, path_prefix: str) -> typing.List[Mapping]:
        """
        Scan IAM roles for Kubernetes user details.

        :param path_prefix: Path prefix to use as a filter. Use "/" to scan all roles.
        :returns: List of IAM role to K8s user mappings found.

        Each IAM role is scanned for the following tags (`{cluster}` is replaced with the
        cluster name):

        * `eks/{cluster}/username`:
          Username in the Kubernetes cluster.
          This tag is required for the IAM role to be used in the cluster.
        * `eks/{cluster}/groups`:
          List of groups for the user in Kubernetes in comma-separated format.
        * `eks/{cluster}/type`:
          Type of the role. "user" = normal k8s user. "node" = a worker node user.
        """
        self._logger.debug("fetching IAM roles", path_prefix=path_prefix)
        paginator = self._iam_client.get_paginator("list_roles")
        mappings: typing.List[Mapping] = []
        for roles in paginator.paginate(PathPrefix=path_prefix):
            for role in roles.get("Roles", []):
                mapping = self._role_to_mappings(role)
                if mapping:
                    mappings.append(mapping)
        return mappings

    def from_iam_users(self, path_prefix: str) -> typing.List[Mapping]:
        """
        Scan IAM users for Kubernetes user details.

        :param path_prefix: Path prefix to use as a filter. Use "/" to scan all users.
        :returns: List of IAM users to K8s user mappings found.

        Each IAM user is scanned for the following tags (`{cluster}` is replaced with the
        cluster name):

        * `eks/{cluster}/username`:
          Username in the Kubernetes cluster.
          This tag is required for the IAM user to be used in the cluster.
        * `eks/{cluster}/groups`:
          List of groups for the user in Kubernetes in comma-separated format.
        """
        self._logger.debug("fetching IAM users", path_prefix=path_prefix)
        paginator = self._iam_client.get_paginator("list_users")
        mappings: typing.List[Mapping] = []
        for users in paginator.paginate(PathPrefix=path_prefix):
            for user in users.get("Users", []):
                mapping = self._user_to_mappings(user)
                if mapping:
                    mappings.append(mapping)
        return mappings

    def _user_to_mappings(self, user: dict) -> typing.Optional[Mapping]:
        username = user["UserName"]
        arn = f"arn:aws:iam::{self._account_id}:user/{username}"
        tags = _Tags(
            tags=self._iam_client.list_user_tags(UserName=username, MaxItems=100).get(
                "Tags", []
            ),
            cluster=self._cluster,
        )

        k8s_username = tags.k8s_username
        if not k8s_username:
            return None

        return Mapping(
            arn=arn,
            mapping_type=MappingType.UserToUser,
            username=k8s_username,
            groups=tags.k8s_groups,
        )

    def _role_to_mappings(self, role: dict) -> typing.Optional[Mapping]:
        rolename = role["RoleName"]
        arn = f"arn:aws:iam::{self._account_id}:role/{rolename}"
        tags = _Tags(
            tags=self._iam_client.list_role_tags(RoleName=rolename, MaxItems=100,).get(
                "Tags", []
            ),
            cluster=self._cluster,
        )

        mapping_type = tags.mapping_type
        if not mapping_type:
            return None
        k8s_username = tags.k8s_username
        if not k8s_username:
            return None

        return Mapping(
            arn=arn,
            mapping_type=mapping_type,
            username=k8s_username,
            groups=tags.k8s_groups,
        )


def _role_type_to_mapping_type(role_type: str) -> typing.Optional[MappingType]:
    if role_type == "user":
        return MappingType.RoleToUser
    if role_type == "node":
        return MappingType.RoleToNode
    return None


class _Tags:
    def __init__(self, tags: list, cluster: str) -> None:
        self._cluster = cluster
        self._ts = {tag["Key"]: tag["Value"] for tag in tags}

    def _get(self, field: str) -> typing.Optional[str]:
        return self._ts.get(f"eks/{self._cluster}/{field}")

    @property
    def k8s_username(self) -> typing.Optional[str]:
        """ Username in Kubernetes """
        return self._get("username")

    @property
    def k8s_groups(self) -> typing.List[str]:
        """ List of groups for the user in Kubernetes """
        groups_str = self._get("groups")
        if groups_str:
            return groups_str.split(",")
        return []

    @property
    def mapping_type(self) -> typing.Optional[MappingType]:
        """ What the AWS role is mapped to in Kubernetes """
        role_type = self._get("type") or "user"
        if role_type == "user":
            return MappingType.RoleToUser
        if role_type == "node":
            return MappingType.RoleToNode
        return None
