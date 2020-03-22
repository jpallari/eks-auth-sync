# pylint: disable=missing-docstring,invalid-name
import unittest
import localstack_client.session
import botocore
import structlog
from eks_auth_sync import scanner
from eks_auth_sync.mapping import Mapping, MappingType

ACCOUNT_ID = "123456789012"
SESSION = localstack_client.session.Session()
IAM_CLIENT = SESSION.client("iam")
LOG = structlog.get_logger()


# Unfortunately, local stack returns all users regardless of which path prefix is used,
# so we can't test different path prefixes with the scanner. :(
class TestScanner(unittest.TestCase):
    maxDiff = None
    testing_scanner = scanner.Scanner(SESSION, "testing")
    production_scanner = scanner.Scanner(SESSION, "production")

    def test_user_scan(self):
        testing_mappings = self.testing_scanner.from_iam_users("/")
        production_mappings = self.production_scanner.from_iam_users("/")

        self.assertListEqual(
            testing_mappings,
            [
                Mapping(
                    arn=f"arn:aws:iam::{ACCOUNT_ID}:user/seppo",
                    mapping_type=MappingType.UserToUser,
                    username="k8s-seppo",
                    groups=["backend"],
                )
            ],
        )
        self.assertListEqual(
            production_mappings,
            [
                Mapping(
                    arn=f"arn:aws:iam::{ACCOUNT_ID}:user/matti",
                    mapping_type=MappingType.UserToUser,
                    username="k8s-matti",
                    groups=["backend", "frontend"],
                ),
                Mapping(
                    arn=f"arn:aws:iam::{ACCOUNT_ID}:user/teppo",
                    mapping_type=MappingType.UserToUser,
                    username="k8s-teppo",
                    groups=["admin"],
                ),
            ],
        )

    def test_role_scan(self):
        testing_mappings = self.testing_scanner.from_iam_roles("/")
        production_mappings = self.production_scanner.from_iam_roles("/")

        self.assertListEqual(
            testing_mappings,
            [
                Mapping(
                    arn=f"arn:aws:iam::{ACCOUNT_ID}:role/testing-developers",
                    mapping_type=MappingType.RoleToUser,
                    username="k8s-developers",
                    groups=["k8s-developers", "viewer"],
                )
            ],
        )
        self.assertListEqual(
            production_mappings,
            [
                Mapping(
                    arn=f"arn:aws:iam::{ACCOUNT_ID}:role/developers",
                    mapping_type=MappingType.RoleToUser,
                    username="k8s-developers",
                    groups=["k8s-developers", "viewer"],
                ),
                Mapping(
                    arn=f"arn:aws:iam::{ACCOUNT_ID}:role/admins",
                    mapping_type=MappingType.RoleToUser,
                    username="k8s-admins",
                    groups=["k8s-admins"],
                ),
                Mapping(
                    arn=f"arn:aws:iam::{ACCOUNT_ID}:role/default-eks-node",
                    mapping_type=MappingType.RoleToNode,
                    username="",
                    groups=[],
                ),
            ],
        )


def create_user(
    path: str, username: str, cluster: str, k8s_username: str, k8s_groups: list,
):
    tags = []
    if cluster and k8s_username:
        tags = [
            {"Key": f"eks/{cluster}/username", "Value": k8s_username},
            {"Key": f"eks/{cluster}/groups", "Value": ",".join(k8s_groups)},
        ]
    try:
        IAM_CLIENT.create_user(Path=path, UserName=username, Tags=tags)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            LOG.error("user already exists", username=username)
        else:
            raise e


def create_user_role(
    path: str, rolename: str, cluster: str, k8s_username: str, k8s_groups: list,
):
    tags = [
        {"Key": f"eks/{cluster}/type", "Value": "user"},
        {"Key": f"eks/{cluster}/username", "Value": k8s_username},
        {"Key": f"eks/{cluster}/groups", "Value": ",".join(k8s_groups)},
    ]
    assume_role_policy_document = (
        """
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::%s:root"},
            "Action": "sts:AssumeRole"
        }
    }
    """
        % ACCOUNT_ID
    )
    try:
        IAM_CLIENT.create_role(
            Path=path,
            RoleName=rolename,
            Tags=tags,
            AssumeRolePolicyDocument=assume_role_policy_document,
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            LOG.error("role already exists", rolename=rolename)
        else:
            raise e


def create_node_role(
    path: str, rolename: str, cluster: str,
):
    tags = [
        {"Key": f"eks/{cluster}/type", "Value": "node"},
    ]
    assume_role_policy_document = """
    {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    }
    """
    try:
        IAM_CLIENT.create_role(
            Path=path,
            RoleName=rolename,
            Tags=tags,
            AssumeRolePolicyDocument=assume_role_policy_document,
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            LOG.error("role already exists", rolename=rolename)
        else:
            raise e


def setUpModule():
    create_user(
        path="/", cluster="", username="pasi", k8s_username="", k8s_groups=[],
    )
    create_user(
        path="/",
        cluster="testing",
        username="seppo",
        k8s_username="k8s-seppo",
        k8s_groups=["backend"],
    )
    create_user(
        path="/",
        cluster="production",
        username="matti",
        k8s_username="k8s-matti",
        k8s_groups=["backend", "frontend"],
    )
    create_user(
        path="/alt/",
        cluster="production",
        username="teppo",
        k8s_username="k8s-teppo",
        k8s_groups=["admin"],
    )
    create_user_role(
        path="/",
        cluster="testing",
        rolename="testing-developers",
        k8s_username="k8s-developers",
        k8s_groups=["k8s-developers", "viewer"],
    )
    create_user_role(
        path="/",
        cluster="production",
        rolename="developers",
        k8s_username="k8s-developers",
        k8s_groups=["k8s-developers", "viewer"],
    )
    create_user_role(
        path="/",
        cluster="production",
        rolename="admins",
        k8s_username="k8s-admins",
        k8s_groups=["k8s-admins"],
    )
    create_node_role(
        path="/", cluster="production", rolename="default-eks-node",
    )


def tearDownModule():
    users = ["pasi", "seppo", "matti", "teppo"]
    roles = ["testing-developers", "developers", "admins", "default-eks-node"]
    for user in users:
        IAM_CLIENT.delete_user(UserName=user)
    for role in roles:
        IAM_CLIENT.delete_role(RoleName=role)
